# Deployment guide: Video-to-Markdown MCP server on Render

This guide takes you from "four files on my computer" to "my AI chat can read videos".
No prior server experience is needed. Budget about 45 minutes the first time, most of it waiting for the build.

**What you will end up with**

```
AI chat (Claude / ChatGPT / Gemini)  ──►  https://your-app.onrender.com/mcp?key=SECRET
                                              │
                                              ▼
                       download video → transcribe speech → read on-screen text → Markdown
```

**Files in this folder**

| File | What it is |
|---|---|
| `server.py` | The whole server (one tool: `process_video`) |
| `requirements.txt` | Python packages |
| `Dockerfile` | Recipe that builds the server's "computer", including FFmpeg |
| `DEPLOYMENT.md` | This guide |

---

## 1. Why Render and not Netlify?

Two hard reasons, both about what this server does:

1. **FFmpeg is a system program, not a Python package.**
   `yt-dlp`, `faster-whisper` and our frame extraction all call FFmpeg. On Render you give it a `Dockerfile`, so you decide exactly what is installed (`apt-get install -y ffmpeg`). Netlify runs your code as *serverless functions* in a locked-down environment where you cannot install system programs like that.
2. **Videos take minutes, serverless functions give you seconds.**
   Downloading a video, transcribing it and running OCR on every second takes roughly 1–3 minutes. Netlify's regular functions are stopped after a very short time limit (about 10–26 seconds, depending on settings; check Netlify's current docs), and its background functions are for jobs that return nothing right away. An MCP tool call must *wait and answer*, so serverless is the wrong shape.

Render's **Web Service** is a normal always-on program in a container, with plenty of time per request, a real disk, and Docker support. It is the right fit.

Also worth knowing: the AI models (Whisper and EasyOCR) need **RAM** (memory). That drives the plan you choose in step 4.

---

## 2. Put the files on GitHub

Render deploys from a GitHub repository.

1. Create a free account at <https://github.com> if you do not have one.
2. Click **New repository**. Name it `video-mcp-server`. Choose **Private**. Click **Create repository**.
3. On the new repository page click **uploading an existing file**, drag in the four files (`server.py`, `requirements.txt`, `Dockerfile`, `DEPLOYMENT.md`), and click **Commit changes**.

> Do **not** upload a cookies file or secrets to GitHub. Those go into Render (step 6).

---

## 3. (Optional) Test on your own computer first

If you have Docker Desktop installed:

```bash
cd video-mcp-server
docker build -t video-mcp .
docker run --rm -p 10000:10000 video-mcp
```

Open <http://localhost:10000/health>. You should see `{"status":"ok"}`.
The MCP endpoint is `http://localhost:10000/mcp`.

Skip this if you do not use Docker; Render will build it for you.

---

## 4. Deploy on Render

1. Create an account at <https://render.com> (sign in with GitHub; it makes step 3 easier).
2. Click **New +** → **Web Service**.
3. Choose **Build and deploy from a Git repository**, click **Connect** next to `video-mcp-server`. (If it is not listed, click *Configure account* and give Render access to the repository.)
4. Fill the form:
   - **Name**: for example `video-mcp-yourname`. This becomes part of your URL.
   - **Region**: the one closest to you.
   - **Branch**: `main`
   - **Language / Runtime**: **Docker**. Render finds the `Dockerfile` by itself.
   - **Instance Type**: choose one with **at least 2 GB RAM** (for example *Standard*). The *Free* instance (512 MB) will run out of memory while loading the models, and free instances also go to sleep when idle. Check Render's pricing page for the current price.
5. Open **Advanced** and add **Environment Variables**:

   | Key | Value | Why |
   |---|---|---|
   | `SECRET_KEY` | a long random string, e.g. 32 random letters and digits | A password so strangers cannot use your server (and your bill). **Strongly recommended.** |
   | `MAX_VIDEO_SECONDS` | `300` | Refuse videos longer than 5 minutes. |
   | `WHISPER_MODEL` | `base` | `tiny` = faster, `small` = more accurate but needs more RAM. |

   Under **Health Check Path** type `/health`.
6. Click **Create Web Service**.

**Waiting for the build.** Render shows a live log. The first build takes about 10–20 minutes (it installs FFmpeg and PyTorch and downloads the AI models). When the log says the service is **Live**, it is ready.

**Getting your public HTTPS URL.** It is shown at the top of the service page, like:

```
https://video-mcp-yourname.onrender.com
```

Your **MCP URL** is that address plus `/mcp` plus your key:

```
https://video-mcp-yourname.onrender.com/mcp?key=YOUR_SECRET_KEY
```

Check it:

1. Open `https://video-mcp-yourname.onrender.com/health` in a browser. You should see `{"status":"ok"}`.
2. (Optional) Test the tool without any AI client:
   ```bash
   npx @modelcontextprotocol/inspector
   ```
   Choose transport **Streamable HTTP**, paste your MCP URL, click **Connect**, open **Tools**, run `process_video` with a short public video URL.

> Treat the full MCP URL like a password. Anyone who has it can use your server. To change the key, edit `SECRET_KEY` in Render, then re-add the connector with the new URL.

---

## 5. Add it to your AI client

Menus change often. If a button name differs slightly, look for the nearest match. All three clients need the same thing: the **MCP URL** from step 4.

### 5a. Claude (web): Custom Connectors

1. Go to <https://claude.ai> and sign in.
2. Open **Customize → Connectors**.
3. Click **Add custom connector**.
4. Enter a name (for example `Video transcriber`) and paste your MCP URL (the one ending in `/mcp?key=...`).
5. Authentication: choose **No sign-in**. (Your server's protection is the `key` in the URL.)
6. Click **Add**.
7. In a chat, click the **+** button → **Connectors**, and switch your connector on.
8. Try: *"Use the video transcriber on https://www.instagram.com/reel/XXXX/ and summarize it."*

Plans: Free, Pro and Max can add a custom connector for their own account (Free allows one). On **Team / Enterprise**, an Owner adds it under **Organization settings → Connectors**, and members then click **Connect**.

### 5b. ChatGPT: Developer Mode (remote MCP)

Requires a ChatGPT plan that offers Developer Mode (a beta feature, available on Plus/Pro at the time of writing; Business/Enterprise admins may need to allow it).

1. In ChatGPT open **Settings → Connectors**.
2. Open **Advanced settings** and turn on **Developer mode**.
3. Back in **Connectors**, click **Create**.
4. Fill in a **Name** and the **MCP server URL** (your URL ending in `/mcp?key=...`).
5. For **Authentication**, choose **No authentication** if it is offered. (Your protection is the `key` in the URL.) Tick the box saying you trust the application, then click **Create**.
6. Start a **new chat**, click **+** → **More** → **Developer mode**, and select your connector.
7. When ChatGPT proposes a tool call, click **Confirm**.

### 5c. Gemini Spark (and the Gemini app)

Google lets you connect your own MCP server as a **custom app**, and says connected apps can be used in Gemini Spark workflows.

1. On a computer, go to <https://gemini.google.com> (you must add it in the web app; it then appears on mobile too).
2. Click **Settings → Connected Apps**. (If you do not see it, try **Personal Intelligence → Connected Apps**.)
3. Under **Custom apps**, paste your MCP URL into **Add a custom app link**, or click **Add a custom app**.
4. Click **Next** and follow the on-screen instructions.
5. In a prompt, type `@` and pick your app. In Spark, add it as a connected app in your workflow.

Google's current limits for custom apps: you must be 18+, in the US, signed in with a **personal** Google account (not work/school), have **Keep Activity** turned on, and use English. It works in the Gemini web and mobile apps.

> **Honest caveat:** Google's page says Gemini handles OAuth "Dynamic Client Registration" automatically, and asks for credentials if a server does not support it. This V1 server has **no OAuth**, only the secret key in the URL. I could not confirm that Gemini accepts a server without OAuth. If Gemini refuses to connect, the fix is to add OAuth to the server, which is a bigger job than V1. Claude and ChatGPT are the safer first targets.

---

## 6. Instagram: getting past "login required"

Instagram often blocks downloads from cloud servers (data-center IP addresses) and says *login required* or *rate-limit reached*. If that happens:

1. In a desktop browser, log in to Instagram with an account you do not mind risking (use a spare account; Instagram may flag automated access).
2. Export your cookies in **Netscape format** with a browser extension such as "Get cookies.txt LOCALLY", saved as `cookies.txt`.
3. In Render: your service → **Environment → Secret Files → Add Secret File**.
   - **Filename**: `cookies.txt`
   - **Contents**: paste the file's contents.
4. Add the environment variable `COOKIES_FILE` = `/etc/secrets/cookies.txt`.
5. Save. Render redeploys.

Cookies expire, so you may need to repeat this occasionally. Public YouTube and many other sites work without cookies. Only download content you have the right to use, and follow each site's terms.

---

## 7. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Build fails while installing | Check the Render log. Retry the deploy once; package downloads sometimes fail. |
| Service restarts or says "Out of memory" | Not enough RAM. Pick a bigger instance, or set `WHISPER_MODEL` to `tiny`. |
| First request after a long idle is slow | Free instances sleep. Paid instances stay awake. |
| `401 Unauthorized` | The URL is missing `?key=...`, or the key is wrong. |
| "Video was not downloaded…" | Video is private, blocked (see step 6), or longer than `MAX_VIDEO_SECONDS`. |
| The AI client says the tool timed out | The video is too long for that client's wait limit. Lower `MAX_VIDEO_SECONDS` (try `120`). |
| On-screen text list has many near-repeats | Captions that reveal word by word look "new" every second. In `server.py`, lower `SIMILARITY_LIMIT` (for example to `70`) to merge more of them. Raising it keeps more entries. |
| Text in another language is missed | Set `OCR_LANGS` (for example `en,hi`) and also change the language list in the `Dockerfile` preload line. |
| YouTube links fail | YouTube changes often. Redeploy to pick up the latest `yt-dlp`; some videos need extra tools not included in V1. |

---

## 8. What V1 deliberately does not do

- No OAuth login (only a secret key in the URL).
- One video at a time per server.
- CPU only, so a 1-minute video takes roughly 1–3 minutes.
- No saving of results; each call is processed from scratch and the temporary files are deleted.
