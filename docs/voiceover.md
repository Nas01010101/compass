# Voiceover script

Voice: Google Cloud Text-to-Speech, `en-US-Chirp3-HD-Aoede`, project `copilot-gdg-11111801`. Each section is one audio file laid under the matching clip. Captions are burned into `docs/demo.mp4`.

1. Two point two billion people live with a vision impairment. An AI agent could run their errands on the web. But a single hidden line on a page can tell that agent to send their money somewhere else, and a person who cannot see the screen cannot catch it.
2. Compass is a browser agent for blind and low-vision users. Today the user types what they want, and voice is the target. Compass turns that sentence into a mandate: who to pay, how much, and on which site. A Guardian plugin then checks every click and every form fill against the mandate before it reaches Chrome.
3. It runs on Google Cloud. Agent Development Kit agents on Gemini in Vertex A I, Chrome driven through the DevTools M C P server, Web Risk for every address, Model Armor to screen page text for injected instructions, Firestore for receipts, and Cloud Run to host it. This voice comes from Cloud Text-to-Speech.
4. Here the user types: pay my rent to jane at rent dot example, at most twelve hundred dollars. Compass reads the mandate back.
5. The page hides an instruction aimed at the agent. Model Armor flags it, and Compass tells the user.
6. A phishing link is stopped by Web Risk before it loads.
7. The Guardian asks for a yes before it clicks. The user answers, go ahead and pay it, and the payment goes through. A receipt is written to Firestore.
8. Compass is open source. A page can say anything it likes. Only the user decides where the money goes.
