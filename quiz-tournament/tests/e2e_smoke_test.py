import sys
import time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", headless=True)
    page = browser.new_page()
    page.on("console", lambda msg: errors.append(f"CONSOLE {msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(f"PAGEERROR: {exc}"))

    def snap(name):
        page.screenshot(path=f"/tmp/pw_{name}.png")

    print("Loading home page...")
    page.goto(BASE, wait_until="networkidle")
    time.sleep(0.3)
    assert page.query_selector(".brand"), "brand missing"
    snap("01_home")

    print("Switching language to Urdu and back...")
    page.click('.lang-switch button[data-lang="ur"]')
    time.sleep(0.3)
    assert page.evaluate("document.body.dir") == "rtl", "RTL not applied"
    body_text = page.inner_text("body")
    assert "کیٹیگریز" in body_text, f"page content did not re-render in Urdu: {body_text[:200]}"
    snap("02_urdu")
    page.click('.lang-switch button[data-lang="en"]')
    time.sleep(0.2)
    assert "categories" in page.inner_text("body").lower(), "page content did not revert to English"

    print("Registering a new user...")
    page.click('a[href="#/register"]')
    time.sleep(0.3)
    uniq = str(int(time.time()))
    page.fill('input[name="name"]', "Playwright Tester")
    page.fill('input[name="email"]', f"pwtest{uniq}@example.com")
    page.fill('input[name="password"]', "testpass123")
    page.click('#auth-form button[type=submit]')
    time.sleep(0.6)
    snap("03_after_register")
    assert "/play" in page.url or page.url.endswith("#/play"), f"did not land on /play: {page.url}"

    print("Opening categories and starting a quiz...")
    page.goto(f"{BASE}/#/play", wait_until="networkidle")
    time.sleep(0.5)
    cat_card = page.query_selector(".category-card")
    assert cat_card, "no category cards rendered"
    cat_card.click()
    time.sleep(0.6)
    snap("04_quiz_question")
    option_btn = page.query_selector(".option-btn")
    assert option_btn, "no options rendered"
    option_btn.click()
    time.sleep(0.4)
    snap("05_quiz_feedback")
    next_btn = page.query_selector("#next-btn")
    assert next_btn, "next button missing after answering"

    print("Fast-forwarding through remaining questions...")
    for _ in range(15):
        nb = page.query_selector("#next-btn")
        if not nb:
            break
        nb.click()
        time.sleep(0.35)
        opt = page.query_selector(".option-btn:not([disabled])")
        if opt:
            opt.click()
            time.sleep(0.35)
    time.sleep(0.5)
    snap("06_quiz_result")
    assert page.query_selector(".result-hero"), "result screen did not render"

    print("Checking leaderboard page...")
    page.goto(f"{BASE}/#/leaderboard", wait_until="networkidle")
    time.sleep(0.5)
    snap("07_leaderboard")
    assert page.query_selector(".leaderboard-row"), "no leaderboard rows"

    print("Checking profile page...")
    page.goto(f"{BASE}/#/profile", wait_until="networkidle")
    time.sleep(0.5)
    snap("08_profile")
    assert page.query_selector(".badge-card"), "no badge cards on profile"

    print("Checking tournaments list...")
    page.goto(f"{BASE}/#/tournaments", wait_until="networkidle")
    time.sleep(0.5)
    snap("09_tournaments")

    print("Logging in as admin and checking admin panel...")
    page.click('#logout-btn') if page.query_selector('#logout-btn') else None
    time.sleep(0.3)
    page.goto(f"{BASE}/#/login", wait_until="networkidle")
    time.sleep(0.3)
    page.fill('input[name="email"]', "admin@quiz.local")
    page.fill('input[name="password"]', "admin123")
    page.click('#auth-form button[type=submit]')
    time.sleep(0.6)
    page.goto(f"{BASE}/#/admin", wait_until="networkidle")
    time.sleep(0.6)
    snap("10_admin_dashboard")
    assert page.query_selector(".stat-card"), "admin dashboard stat cards missing"

    page.click('#admin-tabs button[data-tab="questions"]')
    time.sleep(0.6)
    snap("11_admin_questions")
    assert page.query_selector("table.data-table"), "admin questions table missing"

    page.click('#admin-tabs button[data-tab="tournaments"]')
    time.sleep(0.6)
    snap("12_admin_tournaments")

    page.click('#admin-tabs button[data-tab="users"]')
    time.sleep(0.6)
    snap("13_admin_users")

    browser.close()

print("\n--- JS ERRORS CAUGHT ---")
if errors:
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("None. All checks passed.")
