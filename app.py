from flask import Flask, render_template, request, redirect, url_for
import sr

app = Flask(__name__)

# start with the form
@app.route("/", methods=["GET"])
def index():
    return render_template("form.html")

@app.route("/result", methods=["POST"])
def result():
    request_id = request.form.get("request_id")
    apiurl = request.form.get("apiurl", "https://api.opensuse.org")
    theme = request.form.get("theme", "light")

    if not request_id or not request_id.isdigit():
        return "Invalid request ID", 400

    return redirect(url_for("show_request", request_id=request_id, apiurl=apiurl, theme=theme))


@app.route("/request/<int:request_id>")
def show_request(request_id):
    apiurl = request.args.get("apiurl", "https://api.opensuse.org")
    theme = request.args.get("theme", "light")

    try:
        html_output = sr.generate_request(apiurl, str(request_id), theme)
        return html_output
    except Exception as e:
        return f"<h2>Error processing request {request_id}:</h2><pre>{e}</pre>", 500


@app.route("/project/<project_name>")
def show_project(project_name):
    apiurl = request.args.get("apiurl", "https://api.opensuse.org")
    theme = request.args.get("theme", "light")

    try:
        html_output = sr.generate_project(apiurl, project_name, theme)
        return html_output
    except Exception as e:
        return f"<h2>Error processing project {project_name}:</h2><pre>{e}</pre>", 500


@app.route("/package/<project_name>/<package_name>")
def show_package(project_name, package_name):
    apiurl = request.args.get("apiurl", "https://api.opensuse.org")
    theme = request.args.get("theme", "light")

    try:
        html_output = sr.generate_package(apiurl, project_name, package_name, theme)
        return html_output
    except Exception as e:
        return f"<h2>Error processing package {project_name}/{package_name}:</h2><pre>{e}</pre>", 500


if __name__ == "__main__":
    app.run(debug=True)
