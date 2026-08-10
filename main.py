import os
import discord
from discord.ext import commands
from discord import app_commands
import json
import base64
import requests
from myserver import server_on  # ดึงระบบรัน 24 ชม. จากไฟล์ Flask

# ==================== ตั้งค่าบอทและ GitHub ====================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  
REPO_OWNER = "ngngxikla-ui"
REPO_NAME = "Bottt"
FILE_PATH = "hwid.json"

# 📌 ค่าลิงก์เชิญเข้าเซิร์ฟเวอร์หลักของคุณ (สามารถเปลี่ยนลิงก์ตรงนี้หรือใส่ใน Environment Variables บน Render ได้)
MAIN_SERVER_INVITE = os.getenv("MAIN_SERVER_INVITE", "https://discord.gg/your-main-server")

# 📌 ดึงค่าผ่าน Environment Variables บน Render
ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "1536234943431053333"))
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID", "1533642657413464247"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  
# ==========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  
bot = commands.Bot(command_prefix="!", intents=intents)

def send_webhook_log(title, description, color):
    """ฟังก์ชันส่งข้อความแจ้งเตือนผ่าน Discord Webhook"""
    if not WEBHOOK_URL:
        return
    payload = {
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": "Luca Shop HWID System Logger"}
        }]
    }
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Webhook Error: {e}")

def get_github_data():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8")
            json_data = json.loads(content)
            
            if "hwids" not in json_data:
                json_data["hwids"] = []
            if "blacklist" not in json_data:
                json_data["blacklist"] = []
            if "server_id" not in json_data:
                json_data["server_id"] = None  # เก็บไอดีเซิร์ฟเวอร์ที่ล็อคไว้
                
            return json_data, data["sha"]
    except Exception as e:
        print(f"Error fetching data: {e}")
    return {"hwids": [], "blacklist": [], "server_id": None}, None

def save_github_data(json_data, sha, commit_message):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    
    json_str = json.dumps(json_data, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": commit_message,
        "content": content_encoded,
        "sha": sha
    }
    
    response = requests.put(url, json=payload, headers=headers)
    return response.status_code in [200, 201]

@bot.event
async def on_ready():
    try:
        await bot.change_presence(activity=discord.Game(name="Roblox"))
        synced = await bot.tree.sync()
        print(f"========================================")
        print(f"  LUCA SHOP BOT - ONLINE SUCCESSFULLY    ")
        print(f"========================================")
        print(f"Logged in as {bot.user} (Synced {len(synced)} commands)")
    except Exception as e:
        print(e)

# 🔍 ฟังก์ชันตรวจสอบแอดมินแบบเรียลไทม์
def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if hasattr(interaction.user, "_roles") and ADMIN_ROLE_ID in interaction.user._roles:
        return True
    if hasattr(interaction.user, "roles"):
        for role in interaction.user.roles:
            if role.id == ADMIN_ROLE_ID:
                return True
    return False

# 🔒 ฟังก์ชันตรวจสอบ Server ID (ป้องกันนำไปใช้เซิร์ฟเวอร์อื่น)
async def check_server_lock(interaction: discord.Interaction) -> bool:
    data, _ = get_github_data()
    locked_server_id = data.get("server_id")
    
    # ถ้ายังไม่ได้ตั้งค่าล็อคเซิร์ฟเวอร์ใดๆ ให้ผ่านได้ (หรือจะบังคับให้ตั้งก่อนก็ได้)
    if not locked_server_id:
        return True
        
    # ถ้าไอดีเซิร์ฟเวอร์ปัจจุบันไม่ตรงกับที่ล็อคไว้
    if str(interaction.guild.id) != str(locked_server_id):
        await interaction.response.send_message(
            f"❌ **ไม่สามารถใช้งานบอทนี้ในเซิร์ฟเวอร์นี้ได้!**\n"
            f"⚠️ บอทตัวนี้ถูกล็อคการใช้งานไว้เฉพาะเซิร์ฟเวอร์ที่กำหนดเท่านั้น\n"
            f"🔗 สนใจใช้งานหรือเข้าสู่คอมมูนิตี้หลัก กรุณาเข้าที่ลิงก์นี้: {MAIN_SERVER_INVITE}",
            ephemeral=True
        )
        return False
    return True

# ==================== คำสั่งจัดการระบบ Server Lock ====================

@bot.tree.command(name="setserver", description="[Admin] ล็อคบอทให้ใช้งานได้เฉพาะเซิร์ฟเวอร์นี้เท่านั้น")
async def setserver(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้นที่สามารถใช้คำสั่งนี้ได้", ephemeral=True)
        return

    await interaction.response.send_message("⏳ กำลังบันทึก Server ID ลงในระบบ...", ephemeral=True)
    data, sha = get_github_data()
    
    current_server_id = str(interaction.guild.id)
    data["server_id"] = current_server_id
    
    success = save_github_data(data, sha, f"Admin Lock Bot to Server: {current_server_id}")
    
    if success:
        await interaction.edit_original_response(content=f"🔒 **ล็อคบอทกับเซิร์ฟเวอร์นี้สำเร็จ!**\n- Server Name: `{interaction.guild.name}`\n- Server ID: `{current_server_id}`")
        send_webhook_log("🔒 มีการตั้งค่า Server Lock", f"**แอดมิน:** {interaction.user.mention}\n**เซิร์ฟเวอร์:** {interaction.guild.name} (`{current_server_id}`)", 16776960)
    else:
        await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาดในการบันทึกข้อมูลลง GitHub")

# ==================== คำสั่งต่างๆ (Commercial Grade) ====================

@bot.tree.command(name="addhwid", description="เพิ่ม HWID เข้าสู่ระบบ (สำหรับลูกค้า)")
@app_commands.describe(hwid="รหัส HWID ของคุณ")
async def addhwid(interaction: discord.Interaction, hwid: str):
    if not await check_server_lock(interaction):
        return

    if not is_admin(interaction) and interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ คำสั่งนี้สามารถใช้งานได้เฉพาะในห้อง <#{ALLOWED_CHANNEL_ID}> เท่านั้นครับ!", 
            ephemeral=True
        )
        return

    await interaction.response.send_message("⏳ กำลังบันทึกข้อมูล HWID ลงในระบบ...", ephemeral=True)
    data, sha = get_github_data()
    
    if hwid in data["hwids"]:
        await interaction.edit_original_response(content=f"⚠️ HWID นี้มีอยู่ในระบบอยู่แล้ว: `{hwid}`")
        return
    
    if hwid in data["blacklist"]:
        await interaction.edit_original_response(content=f"🚫 HWID นี้อยู่ในบัญชีดำ (Blacklist) ไม่สามารถใช้งานได้")
        return

    data["hwids"].append(hwid)
    success = save_github_data(data, sha, f"Customer Add HWID: {hwid}")
    
    if success:
        await interaction.edit_original_response(content=f"✅ เพิ่ม HWID สำเร็จ! คุณสามารถเข้าใช้งานโปรแกรมได้แล้ว: `{hwid}`")
        send_webhook_log("🟢 มีการเพิ่ม HWID ใหม่", f"**ผู้ใช้:** {interaction.user.mention}\n**HWID:** `{hwid}`", 3066993)
    else:
        await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล กรุณาแจ้งแอดมิน")

@bot.tree.command(name="removehwid", description="[Admin] ลบ HWID ออกจากระบบ")
@app_commands.describe(hwid="รหัส HWID ที่ต้องการลบ")
async def removehwid(interaction: discord.Interaction, hwid: str):
    if not await check_server_lock(interaction):
        return
    if not is_admin(interaction):
        await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้นที่สามารถใช้คำสั่งนี้ได้", ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ กำลังดำเนินการลบ HWID...", ephemeral=True)
    data, sha = get_github_data()
    
    if hwid not in data["hwids"]:
        await interaction.edit_original_response(content=f"❌ ไม่พบ HWID นี้ในระบบ: `{hwid}`")
        return

    data["hwids"].remove(hwid)
    success = save_github_data(data, sha, f"Admin Remove HWID: {hwid}")
    
    if success:
        await interaction.edit_original_response(content=f"🗑️ ลบ HWID สำเร็จ: `{hwid}`")
        send_webhook_log("🗑️ มีการลบ HWID ออกจากระบบ", f"**แอดมิน:** {interaction.user.mention}\n**HWID ที่ลบ:** `{hwid}`", 15158332)
    else:
        await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาดในการบันทึกข้อมูลลง GitHub")

@bot.tree.command(name="checkhwid", description="[Admin] ตรวจสอบรายชื่อ HWID และ Blacklist ทั้งหมด")
async def checkhwid(interaction: discord.Interaction):
    if not await check_server_lock(interaction):
        return
    if not is_admin(interaction):
        await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้นที่สามารถใช้คำสั่งนี้ได้", ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ กำลังดึงข้อมูลทั้งหมด...", ephemeral=True)
    data, _ = get_github_data()
    hwids = data.get("hwids", [])
    blacklist = data.get("blacklist", [])
    
    hwid_list_str = "\n".join([f"- `{h}`" for h in hwids]) if hwids else "ไม่มี HWID ในระบบ"
    blacklist_str = "\n".join([f"- `{b}`" for b in blacklist]) if blacklist else "ไม่มี Blacklist ในระบบ"
    
    embed = discord.Embed(title="📊 ข้อมูล HWID ทั้งหมดในระบบ", color=discord.Color.blue())
    embed.add_field(name=f"🟢 HWID ปกติ ({len(hwids)} รายการ)", value=hwid_list_str[:1024], inline=False)
    embed.add_field(name=f"🔴 Blacklist ({len(blacklist)} รายการ)", value=blacklist_str[:1024], inline=False)
    
    await interaction.edit_original_response(content=None, embed=embed)

@bot.tree.command(name="blacklisthwid", description="[Admin] เพิ่ม HWID ลงในบัญชีดำเพื่อระงับการเข้าใช้งาน")
@app_commands.describe(hwid="รหัส HWID ที่ต้องการแบน")
async def blacklisthwid(interaction: discord.Interaction, hwid: str):
    if not await check_server_lock(interaction):
        return
    if not is_admin(interaction):
        await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้นที่สามารถใช้คำสั่งนี้ได้", ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ กำลังดำเนินการแบน HWID...", ephemeral=True)
    data, sha = get_github_data()
    
    if hwid in data["blacklist"]:
        await interaction.edit_original_response(content=f"⚠️ HWID นี้อยู่ใน Blacklist อยู่แล้ว: `{hwid}`")
        return
    
    if hwid in data["hwids"]:
        data["hwids"].remove(hwid)
        
    data["blacklist"].append(hwid)
    success = save_github_data(data, sha, f"Admin Blacklist HWID: {hwid}")
    
    if success:
        await interaction.edit_original_response(content=f"🚫 บล็อกและเพิ่ม HWID ลง Blacklist สำเร็จ: `{hwid}`")
        send_webhook_log("🚫 มีการแบน HWID (Blacklist)", f"**แอดมิน:** {interaction.user.mention}\n**HWID ที่แบน:** `{hwid}`", 16711680)
    else:
        await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาดในการบันทึกข้อมูลลง GitHub")

@bot.tree.command(name="unblacklisthwid", description="[Admin] เอา HWID ออกจากบัญชีดำ")
@app_commands.describe(hwid="รหัส HWID ที่ต้องการปลดแบน")
async def unblacklisthwid(interaction: discord.Interaction, hwid: str):
    if not await check_server_lock(interaction):
        return
    if not is_admin(interaction):
        await interaction.response.send_message("❌ เฉพาะแอดมินเท่านั้นที่สามารถใช้คำสั่งนี้ได้", ephemeral=True)
        return
    
    await interaction.response.send_message("⏳ กำลังดำเนินการปลดแบน...", ephemeral=True)
    data, sha = get_github_data()
    
    if hwid not in data["blacklist"]:
        await interaction.edit_original_response(content=f"❌ ไม่พบ HWID นี้ในรายการ Blacklist: `{hwid}`")
        return

    data["blacklist"].remove(hwid)
    success = save_github_data(data, sha, f"Admin Unblacklist HWID: {hwid}")
    
    if success:
        await interaction.edit_original_response(content=f"✅ ปลดแบล็กลิสต์ HWID สำเร็จ: `{hwid}`")
        send_webhook_log("✅ มีการปลดแบน HWID", f"**แอดมิน:** {interaction.user.mention}\n**HWID ที่ปลด:** `{hwid}`", 65280)
    else:
        await interaction.edit_original_response(content="❌ เกิดข้อผิดพลาดในการบันทึกข้อมูลลง GitHub")

# ==================== เปิดระบบ 24 ชม. และรันบอท ====================
if __name__ == "__main__":
    server_on()  # เปิด Flask Server ควบคู่ไปด้วย
    bot.run(os.getenv('TOKEN'))  # ดึง Token บอทจาก Render
