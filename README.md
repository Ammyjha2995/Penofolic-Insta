# Penofolic Instagram feed bot

Every morning (06:47 IST) this repo:

1. reads economy news feeds: **India** (RBI, Business Standard, Mint, ET, BusinessLine, FE) and
   **World** (US Federal Reserve, ECB, BBC Business, The Guardian, CNBC),
2. picks the **4 most important India stories + 2 world stories**: topic weight + how many outlets
   cover it + freshness, with no repeats. World stories get a "why it matters for India" line,
3. writes a short plain-English summary of each (Claude, optional) and **discards any sentence with a number not in the source**,
4. renders a branded 8-slide "Economy Today" carousel (cover, 4 India + 2 World stories, follow slide),
5. opens a GitHub issue with the slides and caption for you to review.

**You approve by adding the label `approved`** (works from the GitHub phone app). The post goes live within a minute and the issue closes with the Instagram link. To skip a day, close the issue.

Cost: ₹0 for GitHub, Instagram and hosting. Claude summaries cost roughly ₹10 a month; without a key the cards show headlines only.

---

## One-time setup (about 45 minutes)

### A. Instagram account
1. In the Instagram app: **Settings → Account type and tools → Switch to professional account → Business**.
   No Facebook Page is needed.

### B. Meta developer app (gives the bot permission to post)
1. Go to **developers.facebook.com** → log in → **My Apps → Create app**.
2. Name it `Penofolic Feed`. For the use case choose **Manage messaging & content on Instagram** → finish creating the app.
3. Left menu: **App roles → Roles → Add people → Instagram Tester** → enter your Penofolic Instagram username.
4. Accept the invite in Instagram: **Settings → Website permissions → Apps and websites → Tester invites → Accept**.
   *(If Meta says the account can't be added because it belongs to the app's business, skip steps 3–4.)*
5. In the app: **Use cases → Customise → Permissions and features** → make sure
   `instagram_business_basic` and `instagram_business_content_publish` are added.
6. **Instagram → API setup with Instagram login → Generate access tokens → Add account** → log in → Allow →
   **Generate token**. Copy it immediately (it starts with `IGAA…`; it is shown once and lasts 60 days).

This is "Standard Access" for your own account: no app review is needed.

### C. GitHub repository
1. Create a **new public repository** named `penofolic-insta`.
   *Public is needed so Instagram can fetch the slide images. No secrets are stored in the code.*
2. Upload everything in this folder (keep the `.github`, `feedbot`, `fonts`, `assets`, `state`, `queue` folders).
   The `.github` folder is hidden on Mac and Windows: turn on "show hidden files" first, or use GitHub Desktop.
3. **Settings → Secrets and variables → Actions → New repository secret**, add:

| Secret | Value |
|---|---|
| `IG_ACCESS_TOKEN` | the token from step B6 (starts with `IGAA…` or `EAA…`) |
| `IG_USER_ID` | the number shown under your account name in the Meta dashboard (required for `EAA…` tokens) |
| `ANTHROPIC_API_KEY` | *(optional)* from console.anthropic.com → API keys. Add ₹500 ($5) credit; that lasts years at this volume |
| `GH_PAT` | only for `IGAA…` tokens: lets the token renew itself (see below). System-user `EAA…` tokens never expire, so skip it |

   **GH_PAT**: GitHub → your profile photo → **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token** → Repository access: *Only* `penofolic-insta` →
   Permissions: **Secrets: Read and write** → Generate → paste the token as the `GH_PAT` secret.
   Set its expiry to 1 year and add a calendar reminder.

4. **Settings → Actions → General → Workflow permissions → Read and write permissions → Save.**

### D. First run
1. **Actions tab → "1. Daily draft" → Run workflow.**
2. After about 1 minute, open the **Issues tab**: you'll see the slides and caption.
3. Edit the caption in the issue if you like, then add the label **`approved`**.
4. **Actions → "2. Publish approved draft"** runs, and the issue closes with the Instagram link.
5. Optional: **Actions → "3. Refresh Instagram token" → Run workflow** once to confirm token renewal works
   (only works when the token is more than 24 hours old).

From then on it runs every morning on its own.

---

## Everyday use
- **Approve:** add the `approved` label (phone: GitHub app → Issues → the draft → Labels).
- **Skip:** close the issue.
- **Fully automatic (no approval):** Settings → Secrets and variables → Actions → **Variables** →
  add `AUTO_PUBLISH` = `true`. Recommended only after a few weeks of checking drafts.
- **Change time:** edit the `cron` line in `.github/workflows/draft.yml` (time is UTC; IST = UTC + 5:30).
- **Change the India/World mix:** `india_stories` and `world_stories` in `config.yml` (total max 8).
- **Change sources, keywords, hashtags, handle:** edit `config.yml`.

## Troubleshooting
| Symptom | Fix |
|---|---|
| Publish fails with an "access token" error | The token expired. Generate a new one (step B6) and update the `IG_ACCESS_TOKEN` secret. |
| "Only photo or video can be accepted as media type" | Instagram couldn't fetch the image. Check the repo is **public**. Then remove and re-add `approved`. |
| No draft today | Fewer than 5 qualifying stories, or no news matched the keywords. Lower `min_score` in `config.yml`. |
| A feed shows `FAIL` in the Actions log | That source changed its RSS address. Update or remove it in `config.yml`; the others keep working. |
| Posting limit error | Instagram caps the number of API posts per 24 hours. One carousel a day is far below it. |

## Files
```
config.yml                 sources, keywords, number of stories, hashtags
feedbot/news.py            fetch + rank + de-duplicate stories
feedbot/writer.py          Claude summaries with number check, caption
feedbot/cards.py           slide design (1080×1350, navy and gold)
feedbot/instagram.py       Instagram Graph API publishing + token refresh
.github/workflows/         daily draft, publish-on-approve, token refresh
state/posted.json          what has been drafted/posted (prevents repeats)
queue/<date>/              each day's slides, post.json (caption + sources)
```

Local preview (no internet needed): `pip install -r requirements.txt` then
`python -m feedbot preview samples/sample-stories.json` → slides appear in `preview/`.

Fonts: Cormorant Garamond and Manrope, SIL Open Font License (see `fonts/`).

## Risks and how this setup handles them
| Risk | Safeguard / what you should do |
|---|---|
| Wrong or invented figures | AI only sees the feed text; any sentence with a number not in the source is dropped. You still approve each post. |
| Copyright | Own summaries and own design; no publisher photos or article text; sources credited. Don't switch to copying article text. |
| Instagram flags the account | One post a day via the official API is normal use. Don't add mass follow/like/comment automation. |
| Token leak (someone posts as you) | Tokens live only in GitHub Secrets. Never paste them in code, issues or chats. If leaked: revoke in Meta app, generate a new one. |
| Drafts are public before approval | The repo is public, so anyone can see draft slides early. Acceptable for public news; don't put private notes in issues. |
| Investment-advice rules (SEBI) | Content is news summaries with a "Not investment advice" line. Avoid stock tips or buy/sell calls. |
| Employer / conflict-of-interest rules | If you are employed by a bank or public body, check its social-media and outside-activity policy before posting commentary. |
| A feed changes or dies | That source is skipped; others continue. Check the Actions log for `FAIL` monthly. |
| Silent stop | Token renewal or GitHub failures email you (GitHub → Settings → Notifications → Actions: on). |
| Bias or one-sided framing | Prompt requires neutral tone; mix of official (RBI, Fed, ECB) and media sources. Review "why it matters" lines while approving. |
