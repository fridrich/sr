from flask import Flask, render_template, request, redirect, url_for, session, jsonify

import sr

app = Flask(__name__)
app.secret_key="this_is_a_key_to_be_changed" # you should change this

# Default values
DEFAULT_API_URL = "https://api.opensuse.org"
DEFAULT_THEME = "light"

@app.route("/", methods=["GET"])
def index():
    if 'apiurl' not in session:
        session['apiurl'] = DEFAULT_API_URL
    if 'theme' not in session:
        session['theme'] = DEFAULT_THEME

    return render_template("form.html",
                         current_apiurl=session['apiurl'],
                         current_theme=session['theme'])

@app.route("/result", methods=["POST"])
def result():
    request_id = request.form.get("request_id")
    apiurl = request.form.get("apiurl", DEFAULT_API_URL)
    theme = request.form.get("theme", DEFAULT_THEME)

    if not request_id or not request_id.isdigit():
        return "Invalid request ID", 400

    session['apiurl'] = apiurl
    session['theme'] = theme

    # Redirect removing the parameters from the URL
    return redirect(url_for("show_request", request_id=request_id))

@app.route("/request/<int:request_id>")
def show_request(request_id):
    apiurl = session.get('apiurl', DEFAULT_API_URL)
    theme = session.get('theme', DEFAULT_THEME)

    try:
        html_output = sr.generate_request(apiurl, str(request_id), theme)
        return html_output
    except Exception as e:
        return f"<h2>Error processing request {request_id}:</h2><pre>{e}</pre>", 500

@app.route("/update_preferences", methods=["POST"])
def update_preferences():
    """Endpoint to change preferences without reloading everything """
    data = request.get_json()

    if 'theme' in data:
        session['theme'] = data['theme']

    if 'apiurl' in data:
        session['apiurl'] = data['apiurl']

    return jsonify({
        'success': True,
        'theme': session.get('theme'),
        'apiurl': session.get('apiurl')
    })

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
