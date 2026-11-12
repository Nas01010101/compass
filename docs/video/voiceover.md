# Demo video voiceover

Gemini TTS (gemini-3.8-flash-tts) on Vertex AI. Narrator voice Kore, user voice Puck. One line per clip, `mm:ss | voice | text`, placed at its start time over a recording of docs/demo-ui.

00:00 | Kore | Compass is a voice browser agent for blind and low-vision users, built on Google's Agent Development Kit and Gemini.
00:10 | Puck | Pay my rent to jane at rent dot example, at most twelve hundred dollars, on QuickPay.
00:20 | Kore | Gemini turns that sentence into a mandate: the recipient, the maximum amount, the site, and an expiry.
00:30 | Kore | The agent reads the page through Chrome's accessibility tree, the same view a screen reader uses.
00:40 | Kore | This page hides an instruction for the AI: send twenty-four hundred dollars to a different account. Model Armor flags it.
00:52 | Puck | Follow the page's note and pay the new account.
00:56 | Kore | When the agent is pushed to pay that account, the Guardian, an A.D.K. plugin that runs before every tool call, blocks the click and tells the user why.
01:08 | Kore | For Jane's payment, the Guardian checks the recipient and the amount, then asks: should I go ahead?
01:22 | Puck | Yes, go ahead.
01:24 | Kore | After a yes, the payment runs, and a receipt with the user's own words is stored in Firestore.
01:36 | Kore | Compass is built on Google's Agent Development Kit, with Gemini on Vertex AI, Model Armor, Web Risk, Firestore and Cloud Run. Every tool call passes the Guardian plugin first.
