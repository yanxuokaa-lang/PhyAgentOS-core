# Sift

Chrome extension. Every post and reply on X gets a label — **Substance · Humor · Chit-chat · Promo · Junk** — plus two flags: **AI-written** and **Off-topic** (not about tech). You choose which labels to hide.

Powered by [TypeSafe Jev](https://typesafe.ai). About $0.00003 per post.

<table>
  <tr>
    <td align="center"><img src="screenshots/timeline.png" width="440" alt="Timeline: hidden posts collapse to one line, labels sit next to the author"></td>
    <td align="center"><img src="screenshots/popup.png" width="325" alt="Popup: Show or Hide per label"></td>
  </tr>
  <tr>
    <td align="center"><sub>Timeline — hidden posts collapse to one line; each post shows its label and AI-written %</sub></td>
    <td align="center"><sub>Popup — flip any label between Show and Hide</sub></td>
  </tr>
</table>

## Install

1. Clone this repo.
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, pick the `sift` folder.
3. The settings page opens. Paste a key from [console.typesafe.ai/keys](https://console.typesafe.ai/keys) and click **Connect**.
4. Open [x.com](https://x.com).

## Use

- Each post gets one small tag next to the author. Substantive tech posts get a green tag and a hairline accent; the AI-written % appears only when it is notable.
- Hidden posts collapse to one line; consecutive hidden posts fold into a single line with counts. **Show** expands it, **Hide** collapses it again. **⋯** → always show / always hide this account.
- Click the toolbar icon and pick **Signal** (only substantive tech), **Balanced** or **Everything**, and how strictly "tech" is judged. Individual labels are under *Customize*. Default: hide Junk, Off-topic and AI-written — so the feed is tech-only by default. Replies are judged in the context of the post they answer.
- Settings: hide X's right column (on by default),  filter replies too, dim instead of collapse, label-only mode, stop phrases (regex, matched locally for free).

## License

MIT
