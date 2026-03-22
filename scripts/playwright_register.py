"""Playwright自动化注册 - 完整无人值守流程"""

import argparse
import asyncio
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .config import load_config, Config
    from .api import (
        Sub2APIClient,
        Sub2APIError,
        create_client,
        generate_valid_ddg_email,
        is_email_available,
    )
except ImportError:
    from config import load_config, Config
    from api import (
        Sub2APIClient,
        Sub2APIError,
        create_client,
        generate_valid_ddg_email,
        is_email_available,
    )

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class PersonInfo:
    full_name: str
    first_name: str
    last_name: str
    birthday: str
    password: str


FIRST_NAMES = [
    "James",
    "John",
    "Robert",
    "Michael",
    "William",
    "David",
    "Richard",
    "Joseph",
    "Thomas",
    "Charles",
    "Matthew",
    "Anthony",
    "Mark",
    "Donald",
    "Steven",
    "Paul",
    "Andrew",
    "Joshua",
    "Kenneth",
    "Kevin",
    "Brian",
    "George",
    "Edward",
    "Ronald",
    "Timothy",
    "Jason",
    "Jeffrey",
    "Ryan",
    "Jacob",
    "Gary",
    "Mary",
    "Patricia",
    "Jennifer",
    "Linda",
    "Elizabeth",
    "Barbara",
    "Susan",
    "Jessica",
    "Sarah",
    "Karen",
    "Lisa",
    "Nancy",
    "Betty",
    "Margaret",
    "Sandra",
    "Ashley",
    "Dorothy",
    "Kimberly",
    "Emily",
    "Donna",
    "Michelle",
    "Carol",
    "Amanda",
    "Melissa",
    "Deborah",
    "Stephanie",
    "Rebecca",
    "Sharon",
    "Laura",
]

LAST_NAMES = [
    "Smith",
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Garcia",
    "Miller",
    "Davis",
    "Rodriguez",
    "Martinez",
    "Hernandez",
    "Lopez",
    "Gonzalez",
    "Wilson",
    "Anderson",
    "Thomas",
    "Taylor",
    "Moore",
    "Jackson",
    "Martin",
    "Lee",
    "Perez",
    "Thompson",
    "White",
    "Harris",
    "Sanchez",
    "Clark",
    "Ramirez",
    "Lewis",
    "Robinson",
    "Walker",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Scott",
    "Torres",
    "Nguyen",
]


def generate_random_person(account_number: int) -> PersonInfo:
    """Generate random personal information."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    birth_year = random.randint(1990, 2008)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return PersonInfo(
        full_name=f"{first_name} {last_name}",
        first_name=first_name,
        last_name=last_name,
        birthday=f"{birth_year}/{birth_month:02d}/{birth_day:02d}",
        password=f"TestPass{account_number}!@#",
    )


def random_delay(min_ms: int = 1000, max_ms: int = 3000):
    """Add random delay."""
    delay_seconds = random.randint(min_ms, max_ms) / 1000
    time.sleep(delay_seconds)


VERIFICATION_CODE_FILE = Path.home() / ".ddg_reg_verification_code"


async def wait_for_email_code(
    page: Page, timeout: int = 120, poll_interval: int = 5
) -> Optional[str]:
    """
    等待Outlook中的验证码邮件。

    使用 Klavis-strata MCP 读取Outlook，提取验证码。
    需要 Agent 介入调用 MCP，将验证码写入 ~/.ddg_reg_verification_code 文件。
    """
    import re

    start_time = time.time()
    print("\n" + "=" * 60)
    print("[!] Agent 介入: 需要获取邮箱验证码")
    print("=" * 60)
    print("请在 Agent 中执行以下操作：")
    print()
    print("1. 调用 Klavis-strata MCP:")
    print('   server_name: "outlook mail"')
    print('   category_name: "OUTLOOK MESSAGE"')
    print('   action_name: "outlookMail_list_messages"')
    print('   query_params: {"max_results": 10}')
    print()
    print("2. 在返回的邮件中查找 OpenAI/DDG 验证邮件")
    print()
    print("3. 读取邮件内容，提取验证码，格式如: 123456")
    print()
    print("4. 将验证码写入文件:")
    print(f"   echo <验证码> > {VERIFICATION_CODE_FILE}")
    print()
    print("脚本将自动检测验证码文件...")
    print("=" * 60 + "\n")

    while time.time() - start_time < timeout:
        if VERIFICATION_CODE_FILE.exists():
            try:
                code = VERIFICATION_CODE_FILE.read_text().strip()
                if code and re.match(r"^[A-Z0-9]{5,8}$", code, re.IGNORECASE):
                    VERIFICATION_CODE_FILE.unlink()
                    print(f"[OK] 已获取验证码: {code}")
                    return code
            except Exception as e:
                print(f"[ERROR] 读取验证码文件失败: {e}")

        elapsed = int(time.time() - start_time)
        print(f"等待验证码... ({elapsed}s / {timeout}s)")
        await asyncio.sleep(poll_interval)

    print("[ERROR] 获取验证码超时")
    return None


async def register_single_account(
    browser: Browser,
    context: BrowserContext,
    page: Page,
    client: Sub2APIClient,
    person: PersonInfo,
    ddg_email: str,
    ddg_password: str,
    account_number: int,
    config: Config,
) -> dict:
    """注册单个账号的完整自动化流程"""
    result = {
        "success": False,
        "account_number": account_number,
        "email": ddg_email,
        "full_name": person.full_name,
        "error": "",
    }

    try:
        # Step 1: 生成OAuth URL
        print(f"[{account_number}] Generating OAuth URL...")
        auth_response = client.generate_auth_url()
        session_id = auth_response.session_id
        auth_url = auth_response.auth_url
        print(f"[{account_number}] Session ID: {session_id[:20]}...")

        # Step 2: 打开授权页
        print(f"[{account_number}] Opening OAuth page...")
        await page.goto(auth_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
        print(f"[{account_number}] Current URL: {page.url}")

        # Step 3: 点击"注册"链接
        print(f"[{account_number}] Looking for signup/register link...")
        signup_link = page.locator(
            'a:has-text("注册"), a[href="/create-account"], button:has-text("Sign up"), button:has-text("注册")'
        ).first
        try:
            if await signup_link.is_visible(timeout=5000):
                await signup_link.click()
                await asyncio.sleep(5)
                print(f"[{account_number}] Clicked signup, URL: {page.url}")
        except Exception as e:
            print(f"[{account_number}] Signup link error: {e}")

        # Step 4: 输入DDG邮箱
        print(f"[{account_number}] Entering DDG email: {ddg_email}")

        selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[id="email"]',
            'input[autocomplete="email"]',
            'input[type="text"]',
        ]

        email_input = None
        for selector in selectors:
            try:
                email_input = page.locator(selector).first
                if await email_input.is_visible(timeout=5000):
                    print(f"[{account_number}] Found email input with selector: {selector}")
                    break
            except:
                continue

        if not email_input or not await email_input.is_visible():
            raise Exception("Could not find email input")

        await email_input.fill(ddg_email)
        await asyncio.sleep(0.5)

        # 点击Continue/继续
        continue_btn = page.locator(
            'button[type="submit"], button:has-text("Continue"), button:has-text("继续")'
        ).first
        await continue_btn.click()
        await asyncio.sleep(5)
        print(f"[{account_number}] After email submit, URL: {page.url}")

        # Step 5: 输入密码
        print(f"[{account_number}] Entering password...")
        try:
            password_input = page.locator('input[type="password"]')
            if await password_input.first.is_visible(timeout=5000):
                await password_input.fill(ddg_password)
                await asyncio.sleep(1)

                # 点击创建账户
                register_btn = page.locator(
                    'button[type="submit"], button:has-text("Create account"), button:has-text("注册")'
                ).first
                await register_btn.click()
                await asyncio.sleep(5)
                print(f"[{account_number}] After password submit, URL: {page.url}")
            else:
                print(f"[{account_number}] Password input not visible")
        except Exception as e:
            print(f"[{account_number}] Password entry error: {e}")
            await asyncio.sleep(3)

        print(f"[{account_number}] Current URL: {page.url}")

        # Step 7: 检查是否需要人机验证
        print(f"[{account_number}] Checking for CAPTCHA...")
        try:
            has_captcha = (
                await page.locator('text="Verify you are human"').is_visible()
                or await page.locator('text="人机验证"').is_visible()
                or await page.locator('iframe[title="reCAPTCHA"]').is_visible()
            )
        except:
            has_captcha = False

        if has_captcha:
            print(f"[{account_number}] WARNING: CAPTCHA detected, trying to solve...")
            try:
                checkbox = page.locator(".rc-anchor-checkbox").first
                if await checkbox.is_visible():
                    await checkbox.click()
                    await asyncio.sleep(3)
            except:
                pass

        # Step 8: 等待并输入验证码
        print(f"[{account_number}] Waiting for verification code in email...")
        code = await wait_for_email_code(page, timeout=120, poll_interval=10)

        if not code:
            raise Exception("Failed to get verification code from email")

        print(f"[{account_number}] Got verification code: {code}")

        # 输入验证码
        code_inputs = [
            'input[name="code"]',
            'input[placeholder*="code" i]',
            'input[aria-label*="code" i]',
            'input[autocomplete="one-time-code"]',
            'input[type="text"]',
        ]

        code_input = None
        for selector in code_inputs:
            try:
                code_input = page.locator(selector).first
                if await code_input.is_visible(timeout=2000):
                    break
            except:
                continue

        if code_input and await code_input.is_visible():
            await code_input.fill(code)
            await asyncio.sleep(0.5)

            submit_btn = page.locator(
                'button[type="submit"], button:has-text("Verify"), button:has-text("验证"), button:has-text("Continue"), button:has-text("继续")'
            ).first
            await submit_btn.click()
            await asyncio.sleep(8)
            print(f"[{account_number}] After code submit URL: {page.url}")

            # 列出页面状态
            inputs = page.locator("input:visible")
            print(f"[{account_number}] Visible inputs after code: {await inputs.count()}")

        # Step 9: 填写个人信息
        print(f"[{account_number}] Filling personal info...")
        print(f"[{account_number}] Current URL: {page.url}")

        # 列出所有可见的 input
        inputs = page.locator("input:visible")
        input_count = await inputs.count()
        print(f"[{account_number}] Visible inputs: {input_count}")
        for i in range(min(input_count, 10)):
            inp = inputs.nth(i)
            inp_type = await inp.get_attribute("type") or "text"
            inp_name = await inp.get_attribute("name") or ""
            inp_placeholder = await inp.get_attribute("placeholder") or ""
            print(f"  [{i}] type={inp_type}, name={inp_name}, placeholder={inp_placeholder[:30]}")

        # 名字
        first_name_input = page.locator(
            'input[name="firstName"], input[id="firstName"], input[placeholder*="first" i]'
        ).first
        if await first_name_input.is_visible(timeout=3000):
            await first_name_input.fill(person.first_name)
            await asyncio.sleep(0.3)
            print(f"[{account_number}] First name filled: {person.first_name}")
        else:
            print(f"[{account_number}] First name input not found")

        # 姓氏
        last_name_input = page.locator(
            'input[name="lastName"], input[id="lastName"], input[placeholder*="last" i]'
        ).first
        if await last_name_input.is_visible(timeout=3000):
            await last_name_input.fill(person.last_name)
            await asyncio.sleep(0.3)
            print(f"[{account_number}] Last name filled: {person.last_name}")
        else:
            print(f"[{account_number}] Last name input not found")

        # 生日
        birthday_inputs = page.locator(
            'input[name*="birth"], input[id*="birth"], input[placeholder*="birthday" i], select[name*="birth"], select[id*="birth"]'
        )
        if await birthday_inputs.first.is_visible(timeout=3000):
            birthday_count = await birthday_inputs.count()
            if birthday_count >= 3:
                parts = person.birthday.split("/")
                for i, part in enumerate(parts):
                    if i < birthday_count:
                        await birthday_inputs.nth(i).select_option(
                            part if birthday_count > 1 else person.birthday
                        )
            else:
                await birthday_inputs.first.fill(person.birthday)
            await asyncio.sleep(0.3)
            print(f"[{account_number}] Birthday filled: {person.birthday}")

        # 点击继续
        print(f"[{account_number}] Looking for continue button...")
        try:
            continue_btn = page.locator(
                'button[type="submit"], button:has-text("Continue"), button:has-text("继续"), button:has-text("Next"), button:has-text("下一步"), button:has-text("Create account"), button:has-text("注册")'
            ).first
            if await continue_btn.is_visible(timeout=5000):
                await continue_btn.click()
                await asyncio.sleep(5)
                print(f"[{account_number}] Continue clicked, URL: {page.url}")
            else:
                print(f"[{account_number}] Continue button not visible")
                await asyncio.sleep(3)
        except Exception as e:
            print(f"[{account_number}] Continue click error: {e}")
            await asyncio.sleep(3)

        # Step 9.5: 检测手机号验证页面（账号已注册成功，需要重新获取OAuth链接）
        print(f"[{account_number}] Checking for phone verification...")
        phone_verify_patterns = [
            'text="Verify your phone number"',
            'text="verify your phone"',
            'input[placeholder*="phone" i]',
            'input[autocomplete="tel"]',
            'text="手机"',
        ]
        needs_relogin = False
        for pattern in phone_verify_patterns:
            try:
                if await page.locator(pattern).first.is_visible(timeout=1000):
                    print(
                        f"[{account_number}] Phone verification detected, account already registered"
                    )
                    needs_relogin = True
                    break
            except:
                pass

        # Step 9.6: 如果需要登录已注册的账号，重新获取OAuth链接
        login_patterns = [
            'input[type="email"]',
            'input[name="email"]',
            'input[autocomplete="email"]',
            'text="Sign in"',
            'text="Log in"',
            'text="登录"',
        ]
        for pattern in login_patterns:
            try:
                if await page.locator(pattern).first.is_visible(timeout=1000):
                    needs_relogin = True
                    break
            except:
                pass

        if needs_relogin:
            print(f"[{account_number}] Needs re-login, getting new OAuth URL...")
            # 获取新的OAuth链接
            new_auth = client.generate_auth_url()
            new_auth_url = new_auth.auth_url
            new_session_id = new_auth.session_id

            # 用邮箱登录（账号已存在）
            print(f"[{account_number}] Logging in with existing account...")
            email_input = page.locator('input[type="email"], input[name="email"]').first
            await email_input.fill(ddg_email)
            await asyncio.sleep(0.5)

            # 点击继续
            await page.locator(
                'button[type="submit"], button:has-text("Continue"), button:has-text("继续")'
            ).first.click()
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 输入密码
            password_input = page.locator('input[type="password"]').first
            await password_input.fill(ddg_password)
            await asyncio.sleep(0.5)

            # 提交登录
            await page.locator(
                'button[type="submit"], button:has-text("Continue"), button:has-text("Log in"), button:has-text("登录")'
            ).first.click()
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # 更新session_id用于后续创建账号
            session_id = new_session_id
            print(f"[{account_number}] Re-logged in successfully")

        # Step 10: 完成OAuth授权
        print(f"[{account_number}] Completing OAuth authorization...")
        print(f"[{account_number}] Current URL: {page.url}")

        # 查找授权按钮
        auth_btns = [
            'button:has-text("Authorize")',
            'button:has-text("授权")',
            'button:has-text("Allow")',
            'button:has-text("允许")',
            'button:has-text("Continue")',
            'button:has-text("继续")',
        ]

        auth_clicked = False
        for retry in range(3):
            # 列出当前页面按钮
            buttons = page.locator("button:visible")
            btn_count = await buttons.count()
            print(f"[{account_number}] Retry {retry + 1}: Found {btn_count} visible buttons")
            for i in range(min(btn_count, 5)):
                btn_text = await buttons.nth(i).text_content() or ""
                print(f'  [{i}]: "{btn_text.strip()}"')

            for btn_text in auth_btns:
                try:
                    btn = page.locator(btn_text).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        print(f"[{account_number}] Clicked authorization button: {btn_text}")
                        auth_clicked = True
                        break
                except:
                    continue

            if auth_clicked:
                break

            # 如果没找到，刷新页面重试
            print(f"[{account_number}] Authorization button not found, refreshing page...")
            await page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

        if not auth_clicked:
            print(f"[{account_number}] No authorization button found after retries")

        # 等待页面变化
        await asyncio.sleep(5)
        print(f"[{account_number}] After auth click URL: {page.url}")

        # Step 11: 捕获localhost回调
        print(f"[{account_number}] Capturing callback URL...")
        callback_url = None

        # 等待页面URL包含code和state
        try:
            for _ in range(30):  # 最多等30秒
                url = page.url
                if "code=" in url and "state=" in url:
                    callback_url = url
                    break
                await asyncio.sleep(1)
        except:
            pass

        if not callback_url:
            raise Exception("Failed to capture callback URL (timeout)")

        print(f"[{account_number}] Callback URL captured!")

        # Step 12: 调用API创建账号
        print(f"[{account_number}] Creating account via API...")
        import re

        code_match = re.search(r"[?&]code=([^&]+)", callback_url)
        state_match = re.search(r"[?&]state=([^&]+)", callback_url)

        if not code_match or not state_match:
            raise Exception("Invalid callback URL")

        create_response = client.create_account_from_oauth(
            session_id=session_id,
            code=code_match.group(1),
            state=state_match.group(1),
            name=person.full_name,
            group_ids=[config.defaults.group_id],
        )

        result["success"] = True
        result["account_id"] = create_response.id
        result["status"] = create_response.status
        print(
            f"[{account_number}] SUCCESS! Account created: ID={create_response.id}, Status={create_response.status}"
        )

    except Exception as e:
        result["error"] = str(e)
        print(f"[{account_number}] ERROR: {e}")

    return result


def get_emails_from_args(emails_str: str, passwords_str: str = "") -> tuple[list, list]:
    """从命令行参数解析邮箱和密码"""
    emails = [e.strip() for e in emails_str.split(",") if e.strip()]
    passwords = [p.strip() for p in passwords_str.split(",")] if passwords_str else []
    return emails, passwords


async def main_async(args):
    """异步主函数"""
    print(f"\n{'=' * 60}")
    print("OpenAI + DuckDuckGo Automated Registration")
    print(f"{'=' * 60}\n")

    # 获取邮箱和密码
    ddg_emails = []
    ddg_passwords = []

    if args.emails:
        ddg_emails, ddg_passwords = get_emails_from_args(args.emails, args.passwords or "")

    if not ddg_emails:
        print("No DDG emails provided. Use -e 'email1,email2' -p 'pass1,pass2'")
        print(
            "Example: python -m scripts.playwright_register -e 'a@duck.com,b@duck.com' -p 'Pass1,Pass2' -c 2"
        )
        return

    if not ddg_emails:
        print("No DDG emails provided. Exiting.")
        return

    # 如果邮箱数量不够，循环使用最后一个
    while len(ddg_emails) < args.count:
        ddg_emails.append(ddg_emails[-1])
        if ddg_passwords:
            ddg_passwords.append(ddg_passwords[-1] if ddg_passwords else "")

    print(f"\n{'=' * 60}")
    print("Step 2: Starting Registration")
    print(f"{'=' * 60}")
    print(f"Total emails: {len(ddg_emails)}")
    print(f"Accounts to register: {args.count}")
    print()

    # 加载配置
    try:
        config = load_config()
        print("Configuration loaded successfully\n")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run 'python -m scripts.setup' first")
        return

    # 创建API客户端
    client = create_client(config)

    try:
        if not client.test_connection():
            print("Connection test failed, but continuing with demo mode...\n")
        else:
            print("Connection successful!\n")
    except Sub2APIError as e:
        print(f"Connection failed: {e}")
        print("Continuing with demo mode...\n")

    # 检查哪些邮箱已注册
    print("Checking email availability...")
    registered_emails = set()
    try:
        for acc in client.get_accounts():
            registered_emails.add(acc.email.lower())
        print(f"Found {len(registered_emails)} registered emails\n")
    except Exception as e:
        print(f"Could not fetch accounts (demo mode): {e}")
        print("Continuing with demo mode...\n")
        # 过滤掉已注册的邮箱 (demo mode - use all emails)
    available_emails = ddg_emails[:]
    available_passwords = []
    for i, email in enumerate(ddg_emails):
        if i < len(ddg_passwords):
            available_passwords.append(ddg_passwords[i])

    print(f"Found {len(available_emails)} available email(s)\n")

    # 如果需要注册的数量大于可用邮箱数，只注册可用的
    actual_count = min(args.count, len(available_emails))
    headless_mode = getattr(args, "headless", True)
    proxy_url = getattr(args, "proxy", None) if not getattr(args, "no_proxy", False) else None
    mode_str = "headless" if headless_mode else "visible"
    print(f"Starting Playwright browser ({mode_str} mode)...")
    if proxy_url:
        print(f"Using proxy: {proxy_url}")
    else:
        print("Proxy: disabled")

    playwright = await async_playwright().start()

    launch_options = {
        "headless": headless_mode,
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if proxy_url:
        if proxy_url.startswith("http://"):
            # Playwright expects proxy URL without protocol prefix for HTTP proxies
            proxy_url_clean = proxy_url.replace("http://", "")
        else:
            proxy_url_clean = proxy_url
        launch_options["proxy"] = {"server": proxy_url_clean}

    browser = await playwright.chromium.launch(**launch_options)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    )
    page = await context.new_page()

    results = []
    skipped_results = []

    try:
        for i in range(actual_count):
            account_number = i + 1

            # 获取对应的邮箱和密码
            ddg_email = available_emails[i]
            ddg_password = available_passwords[i] if i < len(available_passwords) else ""

            # 如果没有密码，随机生成
            if not ddg_password:
                import secrets
                import string

                password_chars = string.ascii_letters + string.digits
                ddg_password = "".join(secrets.choice(password_chars) for _ in range(16))
                print(f"[{account_number}] Generated random password for {ddg_email}")
                # 保存密码到文件
                password_file = Path.home() / ".ddg_reg_passwords.txt"
                with open(password_file, "a", encoding="utf-8") as f:
                    f.write(f"{ddg_email}:{ddg_password}\n")
                print(f"[{account_number}] Password saved to {password_file}")

            # 生成个人信息
            person = generate_random_person(account_number)

            print(f"\n[{account_number}/{actual_count}] Processing: {ddg_email}")

            # 注册账号
            result = await register_single_account(
                browser=browser,
                context=context,
                page=page,
                client=client,
                person=person,
                ddg_email=ddg_email,
                ddg_password=ddg_password,
                account_number=account_number,
                config=config,
            )

            results.append(result)

            # 等待下一个账号
            if i < args.count - 1:
                delay_seconds = args.delay / 1000
                print(f"[{account_number}] Waiting {delay_seconds}s before next account...")
                await asyncio.sleep(delay_seconds)

    finally:
        await browser.close()
        await playwright.stop()

    # 显示结果
    print(f"\n{'=' * 60}")
    print("Registration Summary")
    print(f"{'=' * 60}")

    success_count = len([r for r in results if r.get("success")])
    for r in results:
        status = "SUCCESS" if r.get("success") else "FAILED"
        email = r.get("email", "-")
        error = r.get("error", "")[:50]
        print(f"  {status}: {email} - {error}")

    print(f"\nTotal: {len(results)}")
    print(f"Success: {success_count}")
    print(f"Failed: {len(results) - success_count}")

    # 保存结果
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": datetime.now().isoformat(), "results": results},
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"\nResults saved to: {output_path}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="Automated ChatGPT account registration")
    parser.add_argument("-c", "--count", type=int, default=1, help="Number of accounts to register")
    parser.add_argument(
        "-d", "--delay", type=int, default=30000, help="Delay between accounts (ms)"
    )
    parser.add_argument(
        "--output", type=str, default="registration-results.json", help="Output file"
    )
    parser.add_argument("-e", "--emails", type=str, help="DDG emails (comma separated)")
    parser.add_argument("-p", "--passwords", type=str, help="DDG passwords (comma separated)")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default)",
    )
    parser.add_argument(
        "--no-headless", action="store_false", dest="headless", help="Show browser window"
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default="http://127.0.0.1:7890",
        help="Proxy URL (default: http://127.0.0.1:7890)",
    )
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy")

    args = parser.parse_args()

    # 如果设置了 --no-proxy，清空代理
    if getattr(args, "no_proxy", False):
        args.proxy = None

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
