
import os
os.environ["BROWSER_EXECUTABLE_PATH"] = "/usr/bin/chromium"
os.environ["BROWSER_ARGS"] = "--no-sandbox --disable-dev-shm-usage"

from flask import Flask, request, jsonify
from botasaurus.browser import browser, Driver, Wait
from botasaurus.window_size import WindowSize
import uuid, time, base64

app = Flask(__name__)
MAX_RETRIES = 3

from botasaurus import config
config.browser_executable_path = "/usr/bin/chromium-browser"

@app.route('/')
def home():
    return '✅ Hello from Flask on Railway!'

# === Botasaurus Automation Task
def lynk_checkout_and_get_qr(url, name, email, bid_price=None):
    result = {}

    @browser(
        profile="lynk_id_user",
        window_size=WindowSize.HASHED,
        wait_for_complete_page_load=True
    )
    def run(driver: Driver, data=None):
        nonlocal result  # make sure we can update the outer `result`

        try:
            driver.enable_human_mode()

            def retry_click(selector, retries=MAX_RETRIES):
                for attempt in range(retries):
                    try:
                        driver.select(selector, wait=Wait.SHORT)
                        driver.click(selector)
                        return True
                    except:
                        driver.short_random_sleep()
                return False

            def retry_type(selector, text, retries=MAX_RETRIES):
                for attempt in range(retries):
                    try:
                        driver.type(selector, text)
                        return True
                    except:
                        driver.short_random_sleep()
                return False

            print("🌐 Opening:", url)
            driver.get(url)

            # Optional: Fill custom price if bid_price exists
            if bid_price is not None:
                custom_price_input = driver.select("#bid_price")
                if custom_price_input:
                    retry_type('#bid_price', str(bid_price))
                else:
                    result.update({
                        "status": "error",
                        "message": "Custom price input field not found"
                    })
                    return

            print("🛒 Clicking 'Buy Now'")
            #driver.get_element_with_exact_text("Buy Now", wait=Wait.SHORT).click()
            driver.click(r'#form > div.W\(100\%\) > div > div > div > button', wait=Wait.SHORT)

            print("📧 Typing email and name")
            retry_type('#payer_email', email)
            time.sleep(1)
            retry_type('#payer_name', name)
            time.sleep(1)

            print("💳 Selecting payment method")
            driver.click('button.block > div.justify-between', wait=Wait.SHORT)
            driver.click('li:nth-of-type(1) li:nth-of-type(3) > label', wait=Wait.SHORT)
            driver.click('#modal-payment-method button', wait=Wait.SHORT)
            driver.click('#agree')
            driver.click('#agree_detail')
            driver.click('#btn-dku', wait=Wait.LONG)

            print("🖼️ Waiting for QR")
            driver.wait_for_element("#QRCodeImage", wait=Wait.LONG)
            qr = driver.select("#QRCodeImage")
            if qr:
                src = driver.get_attribute("#QRCodeImage", "src")
                if src.startswith("data:image"):
                    result.update({
                        "status": "success",
                        "qr_base64": src
                    })
                else:
                    result.update({
                        "status": "error",
                        "message": "QR image is not in base64 format"
                    })
            else:
                result.update({
                    "status": "error",
                    "message": "QR code not found"
                })

        except Exception as e:
            result.update({
                "status": "error",
                "message": str(e)
            })

    run()
    return result

# === Flask Route
@app.route('/lynk-checkout', methods=['POST'])
def receive_checkout():
    try:
        data = request.get_json()
        url = data.get('url')
        name = data.get('name', 'user')
        email = data.get('email')
        bid_price = data.get('bid_price')

        if not name or not email:
            return jsonify({"status": "error", "message": "Missing 'name' or 'email'"}), 400

        result = lynk_checkout_and_get_qr(url, name, email, bid_price)

        if result.get("status") == "success":
            return jsonify({
                "status": "success",
                "qr_base64": result["qr_base64"]
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": result.get("message", "Unknown error")
            }), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
