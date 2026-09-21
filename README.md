# The Private Ledger

A static publication with articles, 60-second briefs, company profiles, search, saved articles, and an editor configuration for Pages CMS. Content is stored in GitHub; no database or API key is required to build the website.

## Run locally

Install Python 3.12 or newer, then from this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/build.py
python -m http.server 8000 --directory _site
```

Open http://localhost:8000. On Windows activate with `.venv\Scripts\activate` instead. Rebuild after changing content. The generated `_site` folder is ignored by Git.

## Edit without code

After this repository is connected to Pages CMS:

1. Open https://app.pagescms.org and sign in with your GitHub account.
2. Select this repository and its production branch.
3. Choose **Articles**, **Companies**, **Homepage and site text**, or **About page**.
4. Edit the form fields. Article Body and company Overview use a visual rich-text editor. The Brief fields control the 60-second summary.
5. Use an image field to choose or upload an image; add descriptive alternative text.
6. Save. Each save updates the repository. Changes to a Published entry go live after the hosting build succeeds.

To create an article, choose Articles → Add, fill in the title, unique lowercase web address (slug), date, sector, summary and body. Choose Draft while preparing it. Set Status to Published and save when ready. Draft entries are omitted from the built site, but remain visible to anyone with repository access. Changing a published entry to Draft removes its public page on the next successful deployment. Keep published slugs unchanged to preserve links. Published records are immediately eligible for publishing; the date field is not a scheduling system.

To change homepage copy, choose Homepage and site text, edit the relevant title, introduction or featured article, then save. Site URL should contain the final production origin. Netlify's URL environment variable supplies its production origin automatically.

## Deploy under your own account

1. Push this complete source folder to your GitHub repository, preferably private while preparing content.
2. Sign in to Netlify under your own account. Add/import a project from GitHub and select that repository and production branch.
3. Netlify reads `netlify.toml`: build command `pip install -r requirements.txt && python3 scripts/build.py`, publish directory `_site`, Python 3.12.
4. Before deploying, decide whether the website is public or requires access protection. A private GitHub repository does **not** make the hosted website private. Configure and verify the host's access controls if privacy is required.
5. In Pages CMS, authorize access to only this repository. The `.pages.yml` file defines the editing forms and image uploads.
6. Save a small homepage edit, watch the Netlify deployment succeed, and verify the updated text at the new URL. This is the end-to-end publishing check required before handoff.
7. Add a custom domain through Netlify's domain settings if desired. Keep the existing site available until the replacement has been verified.

No GitHub repository or Netlify project has yet been connected by this source package. These account steps and the live editing demonstration must be completed before claiming handoff is finished.

## Files

- `content/articles`, `content/companies`, `content/settings`: editable JSON content.
- `media/images`: uploaded images. Some existing article images remain externally hosted at their original URLs.
- `.pages.yml`: Pages CMS editor configuration (JSON is valid YAML).
- `templates`, `assets`, `scripts/build.py`: templates, styles, browser behavior and builder.
- `requirements.txt`, `netlify.toml`: build dependency and hosting configuration.
- `dist`, `.openai`: previous Sites deployment snapshot and configuration, retained for continuity. Netlify builds from the editable source into `_site`; do not manually edit the old snapshot.

## Credentials and recovery

Do not commit passwords, access tokens, private keys or `.env` files. Editor and hosting authentication are managed by their services. GitHub history can restore an earlier content version; reverting that change triggers another hosting build. A failed build requires checking Netlify's deployment log before assuming an edit is live.
