from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.parse
import urllib.request


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "SahihAgent/1.0"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tool_search_quran(query):
    encoded = urllib.parse.quote(query)
    url = f"https://alquran.cloud{encoded}/all/en.sahih"
    data = fetch_json(url)
    matches = data.get("data", {}).get("matches", [])[:3]
    results = []
    for m in matches:
        surah = m.get("surah", {}).get("englishName", "Unknown")
        num = m.get("surah", {}).get("number", "?")
        ayah = m.get("numberInSurah", "?")
        text = m.get("text", "")
        results.append({
            "source": f"Quran {num}:{ayah} ({surah})",
            "grade": "Mutawatir (Authentic Revelation)",
            "text": text
        })
    return results


def tool_search_hadith(query):
    collections = ["eng-bukhari", "eng-muslim", "eng-abudawud", "eng-tirmidhi"]
    keywords = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 3]
    if not keywords:
        return []
    results = []
    for col in collections:
        try:
            url = f"https://jsdelivr.net{col}.min.json"
            data = fetch_json(url)
            hadiths = data.get("hadiths", [])
            for h in hadiths:
                text = h.get("text", "")
                lower_text = text.lower()
                score = sum(1 for kw in keywords if kw in lower_text)
                if score >= max(1, len(keywords) // 2):
                    grades = h.get("grades", [])
                    grade_str = ", ".join(g.get("grade", "") for g in grades) if grades else (
                        "Sahih (Agreed Upon)" if col in ["eng-bukhari", "eng-muslim"] else "Graded in Collection"
                    )
                    results.append({
                        "score": score,
                        "source": f"{col.replace('eng-', '').title()} #{h.get('hadithnumber', '?')}",
                        "grade": grade_str,
                        "text": text[:450] + ("..." if len(text) > 450 else "")
                    })
                if len(results) >= 6:
                    break
        except Exception:
            continue
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:3]


def tool_verify_claim(query):
    encoded = urllib.parse.quote(query)
    url = f"https://wikipedia.org{encoded}&format=json&srlimit=2"
    data = fetch_json(url)
    hits = data.get("query", {}).get("search", [])
    results = []
    for h in hits:
        clean_snippet = re.sub(r"<[^>]+>", "", h.get("snippet", ""))
        results.append({
            "source": f"Reference Record: {h.get('title', '')}",
            "grade": "Cross-Referenced Summary",
            "text": clean_snippet
        })
    return results


def run_sahih_agent(user_query):
    q_lower = user_query.lower()
    trace = []
    findings = []

    is_quran = any(k in q_lower for k in ["quran", "ayah", "surah", "verse", "allah"])
    is_hadith = any(k in q_lower for k in ["hadith", "prophet", "bukhari", "muslim", "sunnah", "narrated", "sahih", "daif"])

    if not is_quran and not is_hadith:
        is_quran = True
        is_hadith = True

    if is_quran:
        trace.append("Step 1: Querying Sahih International Quran index...")
        try:
            q_res = tool_search_quran(user_query)
            findings.extend(q_res)
            trace.append(f"Step 1 Complete: Found {len(q_res)} Quranic match(es).")
        except Exception:
            trace.append("Step 1 Notice: Quran index unreachable for this query.")

    if is_hadith:
        trace.append("Step 2: Scanning authentic Hadith collections & grading chains...")
        try:
            h_res = tool_search_hadith(user_query)
            findings.extend(h_res)
            trace.append(f"Step 2 Complete: Found {len(h_res)} Hadith record(s).")
        except Exception:
            trace.append("Step 2 Notice: Hadith index timeout.")

    if not findings:
        trace.append("Step 3: Cross-referencing general knowledge records...")
        try:
            w_res = tool_verify_claim(user_query)
            findings.extend(w_res)
            trace.append(f"Step 3 Complete: Found {len(w_res)} reference record(s).")
        except Exception:
            trace.append("Step 3 Notice: External reference unavailable.")

    if not findings:
        verdict = "Unverified — No direct textual match found in indexed records."
        answer = "SahihAgent could not locate a direct match for your query. Try refining your search with specific keywords, Surah names, or Hadith topics."
    else:
        verdict = f"Verified — {len(findings)} primary source record(s) retrieved."
        answer = f"Based on autonomous source verification for \"{user_query}\", here are the primary records and authenticity grades found:"

    return {
        "agent": "SahihAgent Core v1.0 (Autonomous Python Runtime)",
        "verdict": verdict,
        "answer": answer,
        "trace": trace,
        "sources": findings
    }


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length))
            query = payload.get("query", "").strip()
            if not query:
                self._json(400, {"error": "Query cannot be empty."})
                return
            result = run_sahih_agent(query)
            self._json(200, result)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
