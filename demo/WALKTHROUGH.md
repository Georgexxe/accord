# Accord walkthrough

Conversational narration using Google Chirp 3 HD Charon, matching the voice used in earlier CivicRight and CutoverProof videos. Actual hosted desktop screenshots and selected screen recordings; waiting time shortened; original AI-assisted animation with deliberately introduced test issues.

## 00-welcome

A film can tell one story in English, and a slightly different one in its subtitles. That's the problem Accord helps you catch.

## 01-sources

Here's The Last Lantern, a short we made for this demo. Fourteen passengers are waiting at a station. We've added subtitles, captions, and a couple of shorter edits. Let's see what changed between them.

## 02-spec

First, we check the story notes. How many passengers are waiting? When do we learn the courier's name? Does the bell matter? Accord suggests these notes from the film, and we check them before using them as a reference.

## 03-findings

Look at this subtitle. It says four passengers, but the original says fourteen. The line from the film is right beside it, so we can check the difference ourselves.

## 04-defects

The same mistake has reached the recap and trailer. There are other problems too: a missing bell caption, a name revealed too early, and a subtitle covering the platform sign.

## 05-proposal

Now let's look at the suggested fix. We can switch between Before and After and see the caption on the film. That makes it much easier to judge whether the change actually works.

## 05b-editor

If something still feels wrong, we can edit it here. Change the wording, adjust when it appears, or move it out of the way. We decide what gets applied.

## 06-verified

Once we approve, Accord updates the tracks and checks them again. In this run, all seven issues are cleared. The revised files are ready to download.

## 07-evidence

The history keeps a record of what was checked and what we approved. Behind that, Gemini investigates using evidence stored in ClickHouse. We also tested a separate lighthouse scene to check the workflow on a different story.

## 08-rollback

And if we need to go back, Undo restores the earlier versions, including the recap and trailer. That's Accord: a way to catch changes to the story, check the fix, and keep the final decision with the reviewer.
