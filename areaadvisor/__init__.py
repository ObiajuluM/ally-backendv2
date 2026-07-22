# the best idea i have is to use service areas in first responder(move it to a new app) and then create a Area advisor for each area, that updates may be 4 times a day.
# Then whenever the users location changes for atleast 10km, tell em what's up


# AI-powered safety intelligence engine.
# Your AI shouldn't only look at Ally alerts.

# Example features:


# Active alerts nearby
# general news
# weather
# promixity to first responders


# Risk Scoring Engine – Collects signals (alerts, weather, history, traffic, reports). -  Produces a deterministic 0–100 score.
# LLM Explainer – Generates a concise human-readable explanation and recommendations from the computed score and evidence.

# Risk Score
# +
# LLM Explanation
# =
# Area Advisor


# ------------------------------------------------
# Robbery within 500m              +30

# Flood alert                      +25

# Heavy rainfall                   +10

# Police station 200m away         -10

# Street lighting                  -5

# ------------------------------------

# Risk = 50
# ------------------------------------------------
# Then GPT turns that into:

# Risk is moderately elevated due to a recent robbery report and heavy rainfall reducing visibility. A police station nearby slightly lowers the overall concern.

# The score remains reproducible.


# 0-20
# Safe

# 21-40
# Low

# 41-60
# Moderate

# 61-80
# High

# 81-100
# Critical

"""Prompt"""

# You are an emergency risk analyst.

# Risk Score:
# 58

# Factors:

# - 2 robbery alerts in last 24 hours

# - Heavy rainfall

# - Police station 350m away

# - Daytime

# Generate:

# - concise explanation

# - practical advice

# Less than 70 words.


# then
# if
# Previous: Moderate
# Current: High
# send a new notification
