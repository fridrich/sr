# OBS sr

You'll need to:
* have a working .oscrc
* install python-Jinja2

You can run it with:
    # python3 sr.py <SR>

The result will be a static page in output/

If you want to change how the diff is shown, look at the end of templates/request.html
there should be a line like this:
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/default.min.css" />

You can change this theme by any other provided at https://highlightjs.org/examples
