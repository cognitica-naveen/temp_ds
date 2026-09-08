# DeepStream Live

Simple local web app for viewing a DeepStream live stream in the browser.

## Run it

1. Open a terminal in this project folder:

```bash
cd /home/cai-admin/projects/temp_ds
```

2. Start a local web server:

```bash
python3 -m http.server 8000
```

3. Open this URL in your browser:

```text
http://localhost:8000/
```

The page will load from `index.html`.

## Requirements

- Python 3
- A modern web browser
- The project files kept in the same folder

## If it does not open

- Make sure the server is still running.
- Confirm you opened the correct URL: `http://localhost:8000/`.
- Do not open `index.html` directly from the filesystem if your browser blocks local resources; use the local server instead.

## Project files

- `index.html` — main app page
- `README.md` — run instructions
