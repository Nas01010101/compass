# Demo video voiceover

Gemini TTS (gemini-3.8-flash-tts, voice Kore) on Vertex AI. One line per clip, `mm:ss | text`, placed at its start time over a recording of docs/demo-ui.

00:00 | Compass is a voice browser agent for blind and low-vision users, built on Google's Agent Development Kit and Gemini.
00:10 | The user says what they want, with limits: pay my rent to Jane, at most twelve hundred dollars.
00:20 | Gemini turns that sentence into a mandate: the recipient, the maximum amount, the site, and an expiry.
00:30 | The agent reads the page through Chrome's accessibility tree, the same view a screen reader uses.
00:40 | This page hides an instruction for the AI: send twenty-four hundred dollars to a different account. Model Armor flags it.
00:55 | When the agent is pushed to pay that account, the Guardian blocks the click and tells the user why.
01:08 | For Jane's payment, the Guardian checks the recipient and the amount, then asks: should I go ahead?
01:22 | After a yes, the payment runs, and a receipt with the user's own words is stored in Firestore.
01:36 | Every tool call passes the Guardian first. Page text is data, never instructions. That's Compass.
