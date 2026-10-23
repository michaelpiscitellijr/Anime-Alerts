import json, os, urllib.request

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
USERNAME = os.environ["ANILIST_USERNAME"]
STATE = "posted.json"
API = "https://graphql.anilist.co"

def gql(query, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)["data"]

# 1. Shows you're currently watching
watching = gql("""
query ($user: String) {
  MediaListCollection(userName: $user, type: ANIME, status: CURRENT) {
    lists { entries { mediaId } }
  }
}""", {"user": USERNAME})
ids = [e["mediaId"] for l in watching["MediaListCollection"]["lists"] for e in l["entries"]]
if not ids:
    raise SystemExit("No shows on the Watching list.")

# 2. Last three episodes that have aired
import time
data = gql("""
query ($ids: [Int], $now: Int) {
  Page(perPage: 3) {
    airingSchedules(mediaId_in: $ids, airingAt_lesser: $now, sort: TIME_DESC) {
      id
      episode
      airingAt
      media {
        siteUrl
        title { romaji english }
        coverImage { large }
      }
    }
  }
}""", {"ids": ids, "now": int(time.time())})
episodes = data["Page"]["airingSchedules"]

# 3. Skip ones already posted
posted = json.load(open(STATE)) if os.path.exists(STATE) else []
new = [e for e in reversed(episodes) if e["id"] not in posted]

# 4. Post to Discord (oldest first)
for e in new:
    m = e["media"]
    title = m["title"]["english"] or m["title"]["romaji"]
    payload = {"embeds": [{
        "title": f"{title} – Episode {e['episode']}",
        "url": m["siteUrl"],
        "description": "A new episode just aired.",
        "image": {"url": m["coverImage"]["large"]},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(e["airingAt"])),
    }]}
    req = urllib.request.Request(
        WEBHOOK, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "anilist-webhook"},
    )
    urllib.request.urlopen(req)
    posted.append(e["id"])
    time.sleep(1)

json.dump(posted[-100:], open(STATE, "w"))
