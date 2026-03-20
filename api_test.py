"""
APXMIND full API smoke test
Run: python api_test.py
"""
import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"
token = None
results = []


def req(method, path, body=None, auth=True, label=None):
    global token
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth and token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            resp_body = json.loads(resp.read())
            status = resp.status
    except urllib.error.HTTPError as e:
        try:
            resp_body = json.loads(e.read())
        except Exception:
            resp_body = {}
        status = e.code
    except Exception as e:
        resp_body = {"_error": str(e)}
        status = 0

    tag = label or f"{method} {path}"
    ok = 200 <= (status or 0) < 300
    results.append((tag, status, ok, resp_body))
    icon = "OK" if ok else "FAIL"
    print(f"  [{icon}] [{status}] {tag}")
    if not ok:
        detail = resp_body.get("detail") or resp_body.get("_error") or ""
        if detail:
            print(f"         -> {detail}")
    return resp_body, status


# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("APXMIND API SMOKE TEST")
print("=" * 60)

# ── System ────────────────────────────────────────────────────────────────────
print("\n[System]")
req("GET", "/health", auth=False)
req("GET", "/api", auth=False)

# ── Auth ──────────────────────────────────────────────────────────────────────
print("\n[Auth]")
uid = int(time.time())
body, _ = req("POST", "/api/auth/register", {
    "name": f"testuser_{uid}",
    "password": "test1234",
    "email": f"test_{uid}@neet.ai",
    "current_class": "12th",
    "strong_subjects": ["biology"],
    "weak_subjects": ["physics"],
}, auth=False, label="POST /api/auth/register")
token = body.get("token", "")

body2, _ = req("POST", "/api/auth/login", {
    "name": f"testuser_{uid}", "password": "test1234"
}, auth=False, label="POST /api/auth/login (by name)")
req("POST", "/api/auth/login", {
    "username": body.get("user", {}).get("username", ""), "password": "test1234"
}, auth=False, label="POST /api/auth/login (by username)")

req("GET", "/api/auth/me")
req("GET", "/api/auth/users", auth=False)
req("PUT", "/api/auth/profile", {
    "timezone": "Asia/Kolkata", "learning_level": "intermediate",
    "daily_study_target_hours": 5.0,
})

# ── Subjects ──────────────────────────────────────────────────────────────────
print("\n[Subjects]")
req("GET", "/api/subjects", auth=False)
sbody, _ = req("GET", "/api/subjects/biology/lessons", auth=False)
lessons = sbody.get("lessons", [])
lesson_id = lessons[0]["id"] if lessons else None
if lesson_id:
    req("POST", f"/api/subjects/biology/lessons/{lesson_id}/complete",
        label=f"POST lesson {lesson_id} complete")
    req("POST", f"/api/subjects/biology/lessons/{lesson_id}/complete",
        label="POST lesson complete (idempotent 2nd call)")

# ── Dashboard / Progress ──────────────────────────────────────────────────────
print("\n[Dashboard & Progress]")
req("GET", "/api/dashboard/summary")
req("GET", "/api/progress/daily")
req("GET", "/api/progress/gamification")
req("POST", "/api/progress/study-minutes", {"minutes": 45, "subject": "biology"})

# ── Quiz v2 ───────────────────────────────────────────────────────────────────
print("\n[Quiz]")
qbody, _ = req("POST", "/api/quiz", {
    "subject": "biology", "difficulty": "easy", "question_count": 3,
}, label="POST /api/quiz (start)")
quiz_id = qbody.get("quiz", {}).get("id") or qbody.get("id")

req("GET", "/api/quiz", label="GET /api/quiz (list)")

if quiz_id:
    req("GET", f"/api/quiz/{quiz_id}", label="GET /api/quiz/:id")
    qs_body, _ = req("GET", f"/api/quiz/{quiz_id}/questions",
                     label="GET /api/quiz/:id/questions")
    questions = qs_body.get("questions", [])
    q0 = questions[0] if questions else None
    if q0:
        opts = q0.get("options", ["A"])
        req("POST", f"/api/quiz/{quiz_id}/answers", {
            "question_id": q0["id"], "user_answer": opts[0]
        }, label="POST /api/quiz/:id/answers")
        # answer remaining questions
        for q in questions[1:]:
            opts2 = q.get("options", ["A"])
            req("POST", f"/api/quiz/{quiz_id}/answers", {
                "question_id": q["id"], "user_answer": opts2[0]
            }, label=f"POST answer q{q['id']}")
    req("POST", f"/api/quiz/{quiz_id}/finish", label="POST /api/quiz/:id/finish")
    req("GET", f"/api/quiz/{quiz_id}/results", label="GET /api/quiz/:id/results")

# Start a second quiz to test abandon + delete
qbody2, _ = req("POST", "/api/quiz", {
    "subject": "physics", "question_count": 3
}, label="POST /api/quiz (start #2)")
quiz_id2 = qbody2.get("quiz", {}).get("id") or qbody2.get("id")
if quiz_id2:
    req("PATCH", f"/api/quiz/{quiz_id2}/abandon", label="PATCH /api/quiz/:id/abandon")
    req("DELETE", f"/api/quiz/{quiz_id2}", label="DELETE /api/quiz/:id")

# ── Learn sessions ────────────────────────────────────────────────────────────
print("\n[Learn]")
lbody, _ = req("POST", "/api/learn/sessions", {
    "subject": "biology", "title": "Cell Biology Session"
}, label="POST /api/learn/sessions")
sess_id = lbody.get("id") or (lbody.get("session") or {}).get("id")

req("GET", "/api/learn/sessions", label="GET /api/learn/sessions (list)")
if sess_id:
    req("GET", f"/api/learn/sessions/{sess_id}", label="GET /api/learn/sessions/:id")
    req("GET", f"/api/learn/sessions/{sess_id}/messages",
        label="GET /api/learn/sessions/:id/messages")
    req("PATCH", f"/api/learn/sessions/{sess_id}/end",
        label="PATCH /api/learn/sessions/:id/end")

# ── Library ───────────────────────────────────────────────────────────────────
print("\n[Library - Bookmarks]")
bmbody, _ = req("POST", "/api/library/bookmarks", {
    "title": "Photosynthesis Overview",
    "subject": "biology",
    "path": "/learn/biology/photosynthesis",
}, label="POST /api/library/bookmarks")
bm_id = bmbody.get("id")
req("GET", "/api/library/bookmarks")
if bm_id:
    req("GET", f"/api/library/bookmarks/{bm_id}", label="GET bookmark by id")
    req("PATCH", f"/api/library/bookmarks/{bm_id}", {
        "title": "Photosynthesis Overview (updated)"
    }, label="PATCH bookmark")
    req("DELETE", f"/api/library/bookmarks/{bm_id}", label="DELETE bookmark")

print("\n[Library - Notes]")
nbody, _ = req("POST", "/api/library/notes", {
    "title": "Cell Division",
    "content": "Mitosis produces 2 diploid cells. Meiosis produces 4 haploid cells.",
    "subject": "biology",
    "tags": ["cell", "division"],
}, label="POST /api/library/notes")
note_id = nbody.get("id")
req("GET", "/api/library/notes")
req("GET", "/api/library/notes?subject=biology&q=cell", label="GET notes with search")
if note_id:
    req("GET", f"/api/library/notes/{note_id}", label="GET note by id")
    req("PUT", f"/api/library/notes/{note_id}", {
        "title": "Cell Division (updated)", "content": "Updated content."
    }, label="PUT note")
    req("DELETE", f"/api/library/notes/{note_id}", label="DELETE note")

# ── Achievements ──────────────────────────────────────────────────────────────
print("\n[Achievements]")
req("GET", "/api/achievements")
ach, _ = req("GET", "/api/achievements/earned")
badge_list = ach.get("badges", [])
if badge_list:
    bid = badge_list[0].get("badge_id") or badge_list[0].get("id")
    if bid:
        req("GET", f"/api/achievements/{bid}", label="GET achievement by id")

# ── Profile  ──────────────────────────────────────────────────────────────────
print("\n[Profile]")
req("GET", "/api/profile/subjects")
req("PUT", "/api/profile/subjects/biology", {
    "strength": "strong", "priority_rank": 1
}, label="PUT /api/profile/subjects/biology")
req("PUT", "/api/profile/subjects/physics", {
    "strength": "weak", "priority_rank": 2
}, label="PUT /api/profile/subjects/physics")
req("GET", "/api/profile/subjects")
req("DELETE", "/api/profile/subjects/physics", label="DELETE /api/profile/subjects/physics")

# ── Recommendations ───────────────────────────────────────────────────────────
print("\n[Recommendations]")
req("GET", "/api/recommendations")
req("GET", "/api/recommendations?status=active&subject=biology",
    label="GET recommendations (filtered)")

# ── Insights ──────────────────────────────────────────────────────────────────
print("\n[Insights]")
req("GET", "/api/insights/mastery")
req("GET", "/api/insights/mastery/biology")
req("GET", "/api/insights/readiness?days=30")
req("GET", "/api/insights/habits?days=7")

# ─────────────────────────────────────────────────────────────────────────────
print()
print("=" * 60)
passed = sum(1 for _, _, ok, _ in results if ok)
failed = [(tag, st, body) for tag, st, ok, body in results if not ok]
print(f"RESULTS: {passed}/{len(results)} passed")
if failed:
    print(f"\nFAILURES ({len(failed)}):")
    for tag, st, body in failed:
        detail = body.get("detail") or body.get("_error") or ""
        print(f"  [{st}] {tag}")
        if detail:
            print(f"        {detail}")
print("=" * 60)
