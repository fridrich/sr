# SR viewer

This project is a simple, yet powerful, project that fetches and renders a static HTML page for any given OBS (openSUSE Build Service) request, submit or delete request.

## Getting started

To use this project, you will need:

* The following python packages: osc python-Jinja2 and python-Flask

* A working .oscrc file, this will be setup already if you use osc in the command line.

## Usage

###  Flask Web Application

This runs a local web server that allows you to view requests by navigating to a URL in your browser.
Run:

    $ python3 app.py

And then point your browser to  http://127.0.0.1:5000 or directly to http://127.0.0.1:5000/request/<request_id>


### The standlone script

You also can run the standlone script with:

    $ python3 sr.py <SR>

The script will fetch the request data and save the generated HTML file to the `output/` directory.


## Diff Color Themes

The syntax highlighting for the file diffs is powered by the popular Highlight.js library. You can easily change the color scheme to match your preferences.

For that, edit the templates/request.html file. Then find towards the end the link to the file with the code that imports the CSS theme, it should be something like:
`<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css" />`

There are at least a couple of templates depending of the user theme, remove all of that and add only the line with the stylesheet you want to use from from the [Highlight.js](https://highlightjs.org/examples) examples page.

Just don't touch the two scripts related to the javascript part of highlight.min.js 

