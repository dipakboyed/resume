# Resume PDF Generation Design

**Status:** Approved for implementation  
**Decision:** Proceed  
**Audience:** Repository owner and future contributors

## Approved decisions

- The approved draft uses a two-page, one-column executive resume format.
- Employment dates use `Month YYYY - Month YYYY` or `Month YYYY - Present`.
- The Microsoft principal role uses `2004 - 2016` because month details are not available.
- The M.S. degree uses the graduation year `2008`.
- The B.S. degree uses the graduation year `2004`.
- The patent section includes the pending Rubric Engine patent.
- The production build runs on a GitHub-hosted Ubuntu runner.
- The production build does not depend on a local browser, Python installation, or operating system.

The approved draft is `Dipak-Boyed-Resume-Draft-v4.pdf`. The draft proves the layout and content direction only.

The draft does not prove PDF/UA conformance because Edge produced it. The GitHub workflow must produce and validate the final WeasyPrint PDF.

## Executive decision

This repository can produce a one-column resume PDF from the same content as the GitHub Pages site.

The design targets ATS compatibility, PDF/UA-1 conformance, WCAG 2.2 AA, and clear human readability. No tool can guarantee approval by every ATS or every accessibility reviewer.

Use Jekyll to produce semantic HTML. Use WeasyPrint to convert that HTML into a tagged PDF/UA-1 file.

Use one GitHub Actions workflow for three modes:

- Validate each pull request.
- Build and deploy the PDF with GitHub Pages after a push to `main`.
- Build a downloadable artifact from any selected branch through `workflow_dispatch`.

## Current state

The repository contains one resume source in `index.md`. GitHub Pages uses the Minimal theme through the legacy branch build.

The current page includes a large visual resume before the text resume. That image does not belong in the ATS PDF.

The current text uses useful headings and lists. It also contains enough detail to exceed a concise two-page, one-column format.

No custom GitHub Actions workflow exists. The active Pages site deploys from the root of `main`.

## Goals

- Publish a stable PDF link on the existing GitHub Pages site.
- Build the PDF automatically after each accepted change on `main`.
- Build a one-off PDF from any branch without a merge.
- Keep one source of truth for web and PDF content.
- Preserve section order, text order, links, and Unicode text.
- Meet machine-verifiable PDF/UA-1 rules.
- Pass a manual screen-reader review before the first public release.
- Preserve readable typography in a one-column United States Letter layout.
- Detect ATS extraction failures before deployment.

## Non-goals

- Do not promise acceptance by every proprietary ATS.
- Do not add a multi-column or graphic resume template.
- Do not include the visual whiteboard in the PDF.
- Do not tailor content to a job description in the first version.
- Do not publish branch artifacts to the public Pages site.
- Do not create a GitHub Release for every resume edit.

## Requirements

### Functional requirements

1. A push to `main` builds the site and PDF.
2. The same workflow validates both outputs.
3. A successful `main` build deploys both outputs to GitHub Pages.
4. The site links to `/resume/assets/Dipak-Boyed-Resume.pdf`.
5. A manual workflow run accepts any branch through the GitHub branch selector.
6. A manual branch run uploads the PDF as a workflow artifact.
7. A pull request build uploads a preview PDF artifact.
8. A branch or pull request build never deploys to GitHub Pages.
9. Every production and branch build runs on a GitHub-hosted `ubuntu-latest` runner.
10. A build never depends on software installed on the repository owner's machine.

### ATS requirements

- Use one content column.
- Use real text instead of text images.
- Use standard section headings.
- Put contact details in the document body.
- Use simple lists and paragraphs.
- Avoid tables, text boxes, icons, charts, and essential headers or footers.
- Embed one common font family.
- Preserve a logical top-to-bottom text order.
- Preserve visible URLs or descriptive link text.
- Keep the primary resume at exactly two pages.
- Use full month names for employment dates when month data exists.
- Use a four-digit year for each education degree.
- Disable discretionary hyphenation and common ligatures.

The current career scope supports a two-page executive resume. A one-page target will remove too much relevant evidence.

### Accessibility requirements

- Set the document title and language.
- Use one `h1` and a correct heading hierarchy.
- Tag paragraphs, lists, and links with semantic roles.
- Preserve the DOM order as the PDF read order.
- Meet a 4.5:1 contrast ratio for normal text.
- Use at least 10.5-point body text as a project readability rule.
- Mark decorative elements as artifacts or omit them.
- Add useful link text.
- Include no information that depends only on color.
- Produce PDF/UA-1 tags and metadata.

## Proposed architecture

### Content and templates

Move resume facts into `_data/resume.yml`. This file becomes the only source for contact details, summary, experience, education, certifications, skills, and publications.

Create `_includes/resume-content.html` with semantic Liquid markup. Both web and PDF pages use this include.

Keep the visual resume only in `index.md`. Add the shared text include after the visual section.

Create `resume-pdf.html` with `layout: null` and `sitemap: false`. Add `noindex` metadata for search engines.

This page contains a complete HTML document, a title, `lang="en-US"`, metadata, and the shared resume include.

Create `assets/css/resume-print.css`. Use United States Letter pages, one column, fixed margins, and conservative typography.

### Build pipeline

Use `actions/jekyll-build-pages` on `ubuntu-latest` to build `_site`. This action supplies the GitHub Pages Jekyll environment.

Use WeasyPrint with `--pdf-variant pdf/ua-1` against `_site/resume-pdf.html`.

Write the final file to `_site/assets/Dipak-Boyed-Resume.pdf`. Add a download link to the public page.

Use `{{ '/assets/Dipak-Boyed-Resume.pdf' | relative_url }}` for the public link. Set `baseurl: /resume` in `_config.yml`.

Pin the WeasyPrint, validation package, font, action, and veraPDF versions used by the workflow.

Vendor one Open Font License font under `assets/fonts`. Include its license file and embed the font in the PDF.

### GitHub Actions workflow

Create `.github/workflows/resume.yml` with these triggers:

```yaml
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read
```

Use one build job for all triggers. Run source validation, Jekyll, WeasyPrint, accessibility checks, and ATS extraction checks.

Run the build job on `ubuntu-latest`. Upload the PDF artifact for pull requests and manual runs.

Name each artifact with the sanitized branch name and commit SHA. Retain the artifact for 30 days.

Run a separate deploy job only for a push to `main`. Use `actions/configure-pages`, `actions/upload-pages-artifact`, and `actions/deploy-pages`.

Give only the deploy job these permissions:

```yaml
permissions:
  contents: read
  pages: write
  id-token: write

environment:
  name: github-pages

concurrency:
  group: github-pages
  cancel-in-progress: false
```

The workflow file must exist on the default branch before GitHub displays the manual run control. The user can select another branch at run time.

The equivalent CLI command is:

```powershell
gh workflow run resume.yml --ref <branch>
```

GitHub Pages must change from the legacy branch build to the GitHub Actions source during rollout.

Before that switch, run the build job on a feature branch through a temporary branch push trigger. Do not run the deploy job.

After the workflow reaches `main`, use `workflow_dispatch` for one-off builds from any selected branch.

## Validation contract

### Source contract

Validate `_data/resume.yml` against a checked-in schema. Reject missing names, roles, dates, descriptions, links, and required sections.

Reject empty list items, malformed URLs, duplicate experience entries, and date ranges with an invalid order.

### ATS contract

Extract text with default `pdftotext` and `pdftotext -layout`. Compare both normalized outputs with the canonical resume text.

Use default mode for token presence. Use layout mode for the visible top-to-bottom order.

Require these results:

- All required section headings appear in order.
- All job titles, employers, dates, and bullet text appear.
- No replacement characters appear.
- No unexpected text appears before the candidate name.
- All contact and profile links in the canonical data remain extractable.
- The extracted text follows the visible top-to-bottom order.
- The document contains exactly two pages.
- No ligature code points from U+FB00 through U+FB06 appear.
- No soft hyphen appears.
- Every employment date matches the approved date format.
- Both degree records include the approved graduation year.
- The pending Rubric Engine patent appears before issued patents.

This contract detects common ATS failures. It does not represent certification from Workday, Greenhouse, Lever, or another ATS.

Perform one manual import into the target ATS before the first public release. Compare every parsed field with the source resume.

### Accessibility contract

Run axe-core against the standalone PDF HTML with print media active. Run veraPDF against the PDF/UA-1 profile.

Require these results:

- The HTML has no serious or critical axe violations.
- veraPDF reports full machine-verifiable PDF/UA-1 conformance.
- The PDF contains a title, language, tags, bookmarks, and embedded fonts.
- Link annotations match link tags.

Run a WeasyPrint and veraPDF spike before the final CSS work. Stop if the selected versions cannot pass PDF/UA-1.

Use Prince or Antenna House only after a license and cost decision. Do not waive a PDF/UA failure without an explicit owner decision.

veraPDF only checks machine-verifiable PDF/UA rules. Complete one manual review with Adobe Acrobat or PAC and NVDA.

The manual review must confirm headings, lists, links, read order, pronunciation, and keyboard navigation.

### Visual contract

Render each PDF page to an image after the semantic and extraction contracts pass.

Reject clipped text, orphan headings, split role headers, hidden links, and body text below 10.5 points.

Use the approved draft as a review reference. Do not use a pixel-perfect snapshot as a blocking gate for normal content changes.

## Template rules

Use this section order:

1. Name and contact details
2. Executive summary
3. Core skills
4. Professional experience
5. Education and certifications
6. Patents and selected publications

Use reverse chronological experience. Limit each recent role to four or five impact bullets.

Use fewer bullets for older roles. Preserve metrics, scale, ownership, and business outcomes.

Use black or near-black text on a white background. Use one restrained accent color only for headings or links.

Use Source Sans 3 or Noto Sans. Vendor and embed the selected font.

Use `font-variant-ligatures: none` and `hyphens: none`.

Do not put page numbers or essential text in page margins. Some extractors read margin content before the candidate name.

## Options considered

| Option | ATS | Accessibility | CI fit | Decision |
|---|---:|---:|---:|---|
| Browser print through Chromium | Good text extraction | Tagged output varies | Easy | Reject |
| WeasyPrint PDF/UA-1 | Good | Native PDF/UA variants | Good | Select |
| Prince or Antenna House | Good | Strong tagged PDF support | Good | Reserve after license review |
| LibreOffice from DOCX | Good | Export quality varies | Moderate | Reject |
| LaTeX with `tagpdf` | Good | Possible PDF/UA output | Complex | Reject |

WeasyPrint provides the best open-source balance for this small repository. Use Prince or Antenna House only if manual review finds a blocker.

## Delivery plan

### Phase 1: Canonical content

Create the YAML schema, resume data, and shared semantic template. Preserve the public page content.

**Exit gate:** The web page contains all canonical text once, and the source contract passes.

### Phase 2: PDF/UA spike

Run Jekyll, WeasyPrint, and veraPDF on `ubuntu-latest`. Use a temporary feature-branch push trigger.

**Exit gate:** veraPDF reports PDF/UA-1 conformance for a minimal resume sample.

### Phase 3: PDF template and quality gates

Add the approved template, pinned font, ATS extraction, axe-core, metadata, page-count, and visual checks.

**Exit gate:** The final PDF passes all automated contracts and one manual screen-reader review.

### Phase 4: Workflow and Pages cutover

Add pull request, manual branch, and `main` push modes. Upload preview artifacts for non-deploy runs.

Merge the workflow and switch the Pages source to GitHub Actions in one controlled cutover.

Inspect the Pages artifact before the switch. Keep the legacy branch source as the rollback option.

**Exit gate:** A `main` push deploys the site and stable PDF URL from one validated artifact.

### Phase 5: Branch proof

Run `workflow_dispatch` against a test branch. Download the named branch artifact.

**Exit gate:** The branch PDF passes all contracts and no Pages deployment starts.

### Phase 6: ATS field audit

Import the PDF into one target ATS. Compare its candidate fields with `_data/resume.yml`.

**Exit gate:** The ATS parses the name, contact details, employers, roles, dates, education, and skills without false fields.

## Risks and controls

| Risk | Control |
|---|---|
| Proprietary ATS parsers differ | Use two extraction engines and one real ATS import |
| PDF/UA automation misses human issues | Require one manual screen-reader review |
| Resume content exceeds two pages | Add content limits and role-specific bullet budgets |
| Pages migration interrupts the site | Test the Pages artifact before the source switch |
| Font changes alter pagination | Pin and embed the font files |
| Branch runs publish private drafts | Upload artifacts only and block deployment outside `main` |
| Web and PDF content diverge | Render both from `_data/resume.yml` and one shared include |
| Tool updates alter output | Pin tool and action versions, and verify the veraPDF installer checksum |
| Local tools differ from CI | Treat only the GitHub-hosted workflow artifact as production output |
| A public print HTML page creates duplicate search content | Add `noindex` and exclude the page from the sitemap |

## Release policy

Do not create a GitHub Release for normal resume edits. The stable Pages link is the public distribution channel.

Create a tagged release only for a named resume edition, such as `2026-08`. Attach the validated PDF from the same commit.

## Completion rule

Do not mark implementation complete from a local PDF.

Require one successful GitHub Actions run on `ubuntu-latest`. Require one successful `workflow_dispatch` run from a non-default branch.

Require the stable Pages PDF URL to return HTTP 200 with `Content-Type: application/pdf`.

## Evidence

- GitHub supports custom Pages workflows with separate build and deploy jobs: <https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages>
- GitHub supports manual workflow runs and branch selection through `workflow_dispatch`: <https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow>
- WeasyPrint supports PDF/UA variants and uses HTML order for PDF order: <https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html#pdf-standards>
- veraPDF validates machine-verifiable PDF/UA-1 and PDF/UA-2 rules: <https://docs.verapdf.org/validation/>
- WCAG requires programmatic structure: <https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html>
- WCAG requires a meaningful content sequence: <https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html>
- WCAG defines a 4.5:1 contrast threshold for normal text: <https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html>
