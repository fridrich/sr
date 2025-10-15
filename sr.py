#!/usr/bin/env python3

import argparse
import logging
import os

from collections import defaultdict
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import osc
from jinja2 import Environment, FileSystemLoader
from osc.core import http_request

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class RequestID:

    def __init__(self, rid, apiurl):
        self.rid = rid
        self.apiurl = apiurl
        self.creator = None
        self.description = None
        self.package = None
        self.staging = None
        self.action = {}
        self.state = {}
        self.reviews = []
        self.comments = []
        self.results = []
        self.history = []  # This is self.reviews flattened and sorted
        self.issues = []
        self.file_diffs = []

        if "suse.de" in apiurl:
            base_url = "https://build.suse.de"
        else:
            base_url = "https://build.opensuse.org"

        self.package_url = f"{base_url}/package/show/"
        self.project_url = f"{base_url}/project/show/"
        self.build_url = f"{base_url}/package/live_build_log/"
        self.user_url = f"{base_url}/users/"
        self.group_url = f"{base_url}/groups/"
        self.external_url = f"{base_url}/requests/"

def parse_request_xml(req, root):

    if root is None:
        return

    req.creator = root.attrib.get("creator")
    req.description = root.findtext("description", default="")

    # Parse <action>
    action_elem = root.find("action")
    if action_elem is not None:
        source = action_elem.find("source")
        target = action_elem.find("target")
        req.action = {
            "type": action_elem.attrib.get("type"),
            "source_project": (
                source.attrib.get("project") if source is not None else None
            ),
            "source_package": (
                source.attrib.get("package") if source is not None else None
            ),
            "source_rev": source.attrib.get("rev") if source is not None else None,
            "target_project": (
                target.attrib.get("project") if target is not None else None
            ),
            "target_package": (
                target.attrib.get("package") if target is not None else None
            ),
        }

    # Parse <state>
    state_elem = root.find("state")
    if state_elem is not None:
        req.state = {
            "name": state_elem.attrib.get("name"),
            "who": state_elem.attrib.get("who"),
            "when": state_elem.attrib.get("when"),
            "created": state_elem.attrib.get("created"),
            "created_utc": datetime.fromisoformat(
                state_elem.attrib.get("created")
            ).replace(tzinfo=timezone.utc),
            "comment": state_elem.findtext("comment", default=""),
        }
        if req.state["name"] == "superseded":
            req.state["superseded_by"] = state_elem.attrib.get("superseded_by")

    # Parse <review>, and <history>
    for review_elem in root.findall("review"):
        review = {
            "state": review_elem.attrib.get("state"),
            "when": review_elem.attrib.get("when"),
            "who": review_elem.attrib.get("who"),
            "by_user": review_elem.attrib.get("by_user"),
            "by_group": review_elem.attrib.get("by_group"),
            "by_project": review_elem.attrib.get("by_project"),
            "comment": review_elem.findtext("comment", default=""),
            "history": [],
        }

        for hist in review_elem.findall("history"):
            review["history"].append(
                {
                    "who": hist.attrib.get("who"),
                    "when": hist.attrib.get("when"),
                    "description": hist.findtext("description", default=""),
                    "comment": hist.findtext("comment", default=""),
                }
            )

        req.reviews.append(review)

    # Get name of the package
    if req.staging:
        req.package = req.action.get('target_package')
    else:
        req.package = req.action.get('source_package')

    # Order reviews in a history
    req.history = []

    for review in req.reviews:
        for event in review.get("history", []):
            req.history.append(
                {
                    "who": event["who"],
                    "when": datetime.fromisoformat(event["when"]),
                    "description": event["description"],
                    "comment": event["comment"],
                }
            )

    # Sort by 'when'
    req.history.sort(key=lambda x: x["when"])

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for h in req.history:
        delta = now - h["when"]
        if delta.days > 0:
            h["timestamp_relative"] = f"{delta.days} days ago"
        else:
            h["timestamp_relative"] = (
                f"{int(delta.total_seconds() // 3600)} hours ago"
            )


    # if it's not accepted and staged, set the staging project
    req.staging = None
    if req.state["name"] not in ["accepted", "superseded"]:
        for review in req.reviews:
            by_project = review.get("by_project")
            if by_project and "openSUSE:Factory:Staging" in by_project:
                req.staging = by_project


def parse_comments_request_xml(req, root):

    if root is None:
        return

    for comment_elem in root.findall("comment"):
        comment_data = {
            "id": comment_elem.attrib.get("id"),
            "who": comment_elem.attrib.get("who"),
            "when": comment_elem.attrib.get("when"),
            "parent": comment_elem.attrib.get("parent"),
            "text": comment_elem.text.strip() if comment_elem.text else "",
        }
        req.comments.append(comment_data)


def parse_request_diff_and_issues_xml(req, root):

    if root is None:
        return

    issues = []
    diff_files = []

    for action_elem in root.findall("action"):
        sourcediff_elem = action_elem.find("sourcediff")

        for file_elem in sourcediff_elem.findall(".//file"):
            file_data = {
                "state": file_elem.attrib.get("state"),
                "name_old": "",
                "name_new": "",
            }

            old_elem = file_elem.find("old")
            if old_elem is not None:
                file_data["name_old"] = old_elem.attrib.get("name", "")

            new_elem = file_elem.find("new")
            if new_elem is not None:
                file_data["name_new"] =  new_elem.attrib.get("name", "")

            diff_elem = file_elem.find("diff")
            if diff_elem is not None:
                file_data["content"] = diff_elem.text.strip() if diff_elem.text else ""

            # add rename state
            if file_data["name_old"] and file_data["name_new"] and file_data["name_old"] != file_data["name_new"]:
                file_data["state"] = "renamed"

            diff_files.append(file_data)

        # <issues>
        for issue_elem in sourcediff_elem.findall(".//issue"):
            issue_data = {
                "state": issue_elem.attrib.get("state"),
                "tracker": issue_elem.attrib.get("tracker"),
                "name": issue_elem.attrib.get("name"),
                "label": issue_elem.attrib.get("label"),
                "url": issue_elem.attrib.get("url"),
            }
            issues.append(issue_data)

    # Sort the diff_files list: .changes first, then .spec, then the rest
    def sort_priority(filename):
        if filename.endswith(".changes"):
            return 0
        elif filename.endswith(".spec"):
            return 1
        else:
            return 2

    diff_files.sort(key=lambda f: sort_priority(f.get("name_new") or f.get("name_old", "")))

    req.issues = issues
    req.file_diffs = diff_files


def parse_results_xml(req, root):

    if root is None:
        return

    parsed_results = []
    pkg = req.package

    for result in root.findall("result"):

        result_attrs = {
            # "project": result.attrib["project"], - not needed
            "repository": result.attrib["repository"],
            "arch": result.attrib["arch"],
            "code": result.attrib["code"],
            "state": result.attrib["state"]
        }

        for status in result.findall("status"):
            if status.attrib["package"] == pkg or status.attrib["package"].startswith(pkg+":"):
                # Flatten status data into top-level dict, rename 'code' to 'status_code'
                parsed_results.append({
                    **result_attrs,
                    "package": status.attrib["package"],
                    "status_code": status.attrib["code"],
                    "details": status.findtext("details")
                })
            else:
                continue

    # Nested dict: package → repo → arch → list of result dicts
    grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for entry in parsed_results:
        package = entry["package"]
        repo = entry["repository"]
        arch = entry["arch"]
        if entry["status_code"] not in ["excluded", "disabled"]:
            grouped[package][repo][arch].append({
                                'code': entry["code"],
                                'details': entry["details"],
                                'state': entry["state"],
                                'status_code': entry["status_code"]
                                })

    # Convert to regular dicts for jinja2
    req.results = {pkg: {repo: dict(archs) for repo, archs in repos.items()}
                   for pkg, repos in grouped.items()}


def fetch_xml(method, url):
    try:
        f = http_request(method, url)
        return ET.parse(f).getroot()
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def path_dir(directory):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, directory)


def generate_request(apiurl="https://api.opensuse.org", request_id="1", theme="light"):

    # output and templates dir are relative to where the script is running

    templates_dir = path_dir("templates")

    osc.conf.get_config(override_apiurl=apiurl)

    req = RequestID(request_id, apiurl)

    # Get the basic SR data
    root = fetch_xml("GET", f"{apiurl}/request/{request_id}")
    parse_request_xml(req, root)

    # Get the comments
    root = fetch_xml("GET", f"{apiurl}/comments/request/{request_id}")
    parse_comments_request_xml(req, root)

    # Get diff and mentioned issues
    root = fetch_xml("POST", f"{apiurl}/request/{request_id}?cmd=diff&view=xml&withissues=1")
    parse_request_diff_and_issues_xml(req, root)

    # Get build information
    if req.staging:
        root = fetch_xml("GET", f"{apiurl}/build/{req.staging}/_result")
    else:
        # When SR is accepted or not staged, use source project
        root = fetch_xml("GET", f"{apiurl}/build/{req.action["source_project"]}/_result")

    parse_results_xml(req, root)

    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    template = env.get_template("request.html")

    rendered = template.render(
        lastupdate=datetime.now(timezone.utc),
        user_theme = theme,
        request=req
    )

    return rendered


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch and render OBS request data.")
    parser.add_argument("request_id", help="OBS Request ID")

    parser.add_argument(
        "-A", "--api-url",
        default="https://api.opensuse.org",
        help="OBS API base URL (default: https://api.opensuse.org)"
    )

    parser.add_argument(
        "-t", "--theme",
        choices=["light", "dark"],
        default="light",
        help="Bootstrap theme to use (default: light)"
    )

    args = parser.parse_args()

    if args.api_url not in ["https://api.opensuse.org", "https://api.suse.de"]:
        logging.error("Unknown API, I'll default to https://api.opensuse.org'")
        args.api_url = "https://api.opensuse.org"

    page = generate_request(args.api_url, args.request_id, args.theme)

    output_dir = path_dir("output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"sr_{args.request_id}.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(page)

