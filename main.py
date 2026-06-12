import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv

# ─── تحميل التوكن بأمان من ملف .env ───────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "data.json"
COIN_IMG = "coin.png"
TICKET_IMG = "ticket_green.png"

COIN_STR = "🪙" 
TICKET_STR = "🎟️"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # تفعيل الجلب الكامل للأعضاء للتأكد من وجودهم

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── ⚙️ لوحة التحكم في الأسعار والمكافآت ────────────────────────
TICKET_TO_TOKEN_RATIO = 4
DAILY_REWARD_FIXED = 10  
TASK_REWARD = 10         

TASKS_LIST = {
    1: "تسجيل الدخول اليومي في البوت",
    2: "التفاعل والدردشة في الشات العام",
    3: "دعوة صديق جديد للانضمام إلى السيرفر"
}

# النصوص القابلة للتعديل من الإدارة
config_data = {
    "shop_text": "🛒 **متجر MIIX GAMES:**\n1. رتبة مميز - 500 عملة\n2. رتبة أسطوري - 1000 عملة",
    "games_text": "🎲 **قائمة الألعاب المتوفرة:**\n• انتظروا ألعابنا الحماسية القادمة قريباً!",
    "tasks_main_text": "🏆 **قائمة المهام اليومية والأسبوعية:**\n\n",
    "job_tasks_text": "قريباً يتم إضافة المهام"
}

# ─── دوال حفظ وشحن البيانات (JSON) ──────────────────────────────────────────
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def setup_user_data(data, user_id):
    if user_id not in data:
        data[user_id] = {}
    if "balance" not in data[user_id]: data[user_id]["balance"] = 0
    if "tickets" not in data[user_id]: data[user_id]["tickets"] = 0
    if "last_daily" not in data[user_id]: data[user_id]["last_daily"] = None
    if "completed_tasks" not in data[user_id]: data[user_id]["completed_tasks"] = []
    if "inventory" not in data[user_id]: data[user_id]["inventory"] = []  
    if "cards" not in data[user_id]: data[user_id]["cards"] = []          
    return data

# ─── الواجهات والأزرار المسهلة للأعضاء (UI Views) ───────────────────────────────

class BackView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="رجوع ↩️", style=discord.ButtonStyle.danger, custom_id="back_to_main")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MiixMenu()
        embed = discord.Embed(
            title="🎯 القائمة الرئيسية - MIIX GAMES",
            description="مرحباً بك في لوحة تحكم ألعابك وحسابك. اختر من الأزرار في الأسفل للتحكم:",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

# نافذة تحويل التذاكر لنقود
class ConvertModal(discord.ui.Modal, title="♻️ تحويل التذاكر إلى مكس توكن"):
    tickets_input = discord.ui.TextInput(
        label="اكتب عدد التذاكر المراد تحويلها:",
        placeholder="مثال: 4, 8, 12, 40...",
        required=True,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.tickets_input.value)
        except ValueError:
            return await interaction.response.send_message("❌ الرجاء إدخال رقم صحيح فقط!", ephemeral=True)

        if qty <= 0:
            return await interaction.response.send_message("❌ يجب إدخال كمية أكبر من صفر!", ephemeral=True)
        if qty < TICKET_TO_TOKEN_RATIO:
            return await interaction.response.send_message(f"❌ أقل كمية تذاكر يمكنك تحويلها حالياً هي {TICKET_TO_TOKEN_RATIO} تذاكر!", ephemeral=True)

        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        
        if data[user_id]["tickets"] < qty:
            return await interaction.response.send_message("❌ عذراً، أنت لا تملك هذه الكمية من التذاكر في حسابك حالياً!", ephemeral=True)

        tokens_earned = qty // TICKET_TO_TOKEN_RATIO
        remainder = qty % TICKET_TO_TOKEN_RATIO
        actual_converted = qty - remainder

        data[user_id]["tickets"] -= actual_converted
        data[user_id]["balance"] += tokens_earned
        save_data(data)

        embed = discord.Embed(
            title="♻️ عملية تحويل ناجحة بـ الأزرار",
            description=f"✅ قمت بتحويل **{actual_converted}** {TICKET_STR} بنجاح!\n🪙 وحصلت في المقابل على: **{tokens_earned}** {COIN_STR}",
            color=discord.Color.green()
        )
        if remainder > 0:
            embed.set_footer(text=f"ملاحظة: تم إرجاع {remainder} تذاكر لحسابك لأنها لم تكتمل لنصاب التحويل.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# 📦 واجهة أزرار المخزن (تحتوي على بطاقاتي ورجوع)
class StorageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="بطاقاتي 🎴", style=discord.ButtonStyle.secondary, custom_id="storage_cards")
    async def cards_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        
        cards = data[user_id]["cards"]
        if not cards:
            cards_text = "❌ لا توجد لديك أي بطاقات حالياً! يمكنك الحصول عليها عن طريق شراء الباكجات من المتجر قريباً."
        else:
            cards_text = "🎴 **ألبوم بطاقاتك المجمعة:**\n" + "\n".join([f"• {card}" for card in cards])
            
        embed = discord.Embed(title="🎴 ألبوم البطاقات الخاص بك", description=cards_text, color=discord.Color.purple())
        await interaction.response.edit_message(embed=embed, view=BackView())

    @discord.ui.button(label="رجوع ↩️", style=discord.ButtonStyle.danger, custom_id="storage_back")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ProfileSubMenu()
        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        balance = data[user_id]["balance"]
        tickets = data[user_id]["tickets"]
        
        embed = discord.Embed(title="👤 حسابك الإحصائي - MIIX GAMES", color=discord.Color.green())
        embed.add_field(name="الاسم:", value=interaction.user.mention, inline=False)
        embed.add_field(name="رصيد التذاكر الحالية:", value=f"{tickets} {TICKET_STR}", inline=True)
        embed.add_field(name="رصيد التوكن الحالي:", value=f"{balance} {COIN_STR}", inline=True)
        await interaction.response.edit_message(embed=embed, view=view)

# 👤 واجهة قائمة الحساب الفرعية المعدلة
class ProfileSubMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تحويل التذاكر لنقود ♻️", style=discord.ButtonStyle.success, custom_id="profile_convert")
    async def convert_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConvertModal())

    @discord.ui.button(label="مخزني 📦", style=discord.ButtonStyle.primary, custom_id="profile_storage")
    async def storage_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        
        inventory = data[user_id]["inventory"]
        if not inventory:
            items_text = "❌ مخزنك فارغ حالياً! لم تقم بشراء أي أغراض أو رتب من المتجر بعد."
        else:
            items_text = "📦 **الأغراض والرتب التي تمتلكها حالياً:**\n" + "\n".join([f"• {item}" for item in inventory])
            
        embed = discord.Embed(title="📦 مخزن الممتلكات الشخصي", description=items_text, color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=StorageView())

    @discord.ui.button(label="رجوع ↩️", style=discord.ButtonStyle.danger, custom_id="profile_back")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MiixMenu()
        embed = discord.Embed(
            title="🎯 القائمة الرئيسية - MIIX GAMES",
            description="مرحباً بك في لوحة تحكم ألعابك وحسابك. اختر من الأزرار في الأسفل للتحكم:",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

# 🏆 واجهة أزرار المهام 
class TasksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="مهام الوظيفة 💼", style=discord.ButtonStyle.primary, custom_id="tasks_job_btn")
    async def job_tasks_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(config_data["job_tasks_text"], ephemeral=True)

    @discord.ui.button(label="رجوع ↩️", style=discord.ButtonStyle.danger, custom_id="tasks_back_btn")
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MiixMenu()
        embed = discord.Embed(
            title="🎯 القائمة الرئيسية - MIIX GAMES",
            description="مرحباً بك في لوحة تحكم ألعابك وحسابك. اختر من الأزرار في الأسفل للتحكم:",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=view)

class MiixMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="حسابي 👤", style=discord.ButtonStyle.primary, custom_id="menu_profile", row=0)
    async def profile(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        
        balance = data[user_id]["balance"]
        tickets = data[user_id]["tickets"]
        
        embed = discord.Embed(title="👤 حسابك الإحصائي - MIIX GAMES", color=discord.Color.green())
        embed.add_field(name="الاسم:", value=interaction.user.mention, inline=False)
        embed.add_field(name="رصيد التذاكر الحالية:", value=f"{tickets} {TICKET_STR}", inline=True)
        embed.add_field(name="رصيد التوكن الحالي:", value=f"{balance} {COIN_STR}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=ProfileSubMenu())

    @discord.ui.button(label="تسجيل دخول 📆", style=discord.ButtonStyle.success, custom_id="menu_daily", row=0)
    async def daily(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        
        now = datetime.utcnow()
        last_daily_str = data[user_id]["last_daily"]
        
        if last_daily_str:
            last_daily = datetime.fromisoformat(last_daily_str)
            if now - last_daily < timedelta(days=1):
                next_claim = last_daily + timedelta(days=1)
                remaining = next_claim - now
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                
                embed = discord.Embed(
                    title="📆 تسجيل الدخول اليومي",
                    description=f"❌ لقد استلمت مكافأتك اليومية بالفعل!\nعد مجدداً بعد: **{hours} ساعة و {minutes} دقيقة**.",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=BackView())
                return

        data[user_id]["balance"] += DAILY_REWARD_FIXED
        data[user_id]["last_daily"] = now.isoformat()
        
        task_msg = ""
        if 1 not in data[user_id]["completed_tasks"]:
            data[user_id]["completed_tasks"].append(1)
            data[user_id]["balance"] += TASK_REWARD
            task_msg = f"\n\n🏆 **إنجاز مهمة:** لقد أتممت المهمة [1] بنجاح وحصلت على **+{TASK_REWARD}** {COIN_STR} إضافية لتنفيذها!"

        save_data(data)
        
        embed = discord.Embed(
            title="📆 تسجيل الدخول اليومي",
            description=f"✅ تم تسجيل دخولك بنجاح اليوم!\nلقد حصلت على الجائزة الثابتة: **{DAILY_REWARD_FIXED}** {COIN_STR}.{task_msg}",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=BackView())

    @discord.ui.button(label="المهام 🏆", style=discord.ButtonStyle.danger, custom_id="menu_tasks", row=0)
    async def tasks(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        user_id = str(interaction.user.id)
        data = setup_user_data(data, user_id)
        
        user_completed = data[user_id]["completed_tasks"]
        
        tasks_text = config_data["tasks_main_text"]
        for task_id, task_desc in TASKS_LIST.items():
            status_emoji = "✅" if task_id in user_completed else "❌"
            tasks_text += f"{status_emoji} **مهمة رقم {task_id}:** {task_desc} `({TASK_REWARD} توكن)`\n"
            
        embed = discord.Embed(title="🏆 لوحة المهام التفاعلية", description=tasks_text, color=discord.Color.orange())
        embed.set_footer(text="المهمة رقم 1 تنجز تلقائياً عند الضغط على زر تسجيل دخول!")
        await interaction.response.edit_message(embed=embed, view=TasksView())

    @discord.ui.button(label="الألعاب 🎲", style=discord.ButtonStyle.secondary, custom_id="menu_games", row=1)
    async def games(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎲 الألعاب", description=config_data["games_text"], color=discord.Color.purple())
        await interaction.response.edit_message(embed=embed, view=BackView())

    @discord.ui.button(label="المتجر 🛒", style=discord.ButtonStyle.secondary, custom_id="menu_shop", row=1)
    async def shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛒 المتجر", description=config_data["shop_text"], color=discord.Color.gold())
        await interaction.response.edit_message(embed=embed, view=BackView())

    @discord.ui.button(label="توب السنافر 📊", style=discord.ButtonStyle.secondary, custom_id="menu_leaderboard", row=1)
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        sorted_users = sorted(data.items(), key=lambda item: item[1].get("balance", 0), reverse=True)
        
        leaderboard_text = "📊 **قائمة أغنى 20 سنفور في السيرفر (MIIX TOKENS):**\n\n"
        
        count = 0
        for user_id, user_info in sorted_users:
            if count >= 20:
                break
            
            member = interaction.guild.get_member(int(user_id))
            if not member:
                continue
                
            user_name = member.display_name
            balance = user_info.get("balance", 0)
            
            if count == 0:
                medal = "🥇"
            elif count == 1:
                medal = "🥈"
            elif count == 2:
                medal = "🥉"
            else:
                medal = f"#{count+1}"
                
            leaderboard_text += f"{medal} **{user_name}** — `{balance}` {COIN_STR}\n"
            count += 1
            
        if count == 0:
            leaderboard_text += "المشهد هادئ جداً هنا.. لا يوجد سنافر يملكون نقوداً حتى الآن! 🪙"
            
        embed = discord.Embed(title="💙 لوحة توب السنافر - Mix Games", description=leaderboard_text, color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=BackView())

# ─── لوحة تحكم الإدمن لأمر /Em ────────────────────────────────────────────────
class AdminModal(discord.ui.Modal):
    def __init__(self, category_key, title_name):
        super().__init__(title=f"تعديل نص {title_name}", custom_id=f"admin_modal_{category_key}")
        self.category_key = category_key
        
        self.text_input = discord.ui.TextInput(
            label="اكتب النص الجديد هنا:",
            style=discord.TextStyle.long,
            default=config_data[category_key],
            required=True,
            custom_id=f"admin_input_{category_key}"
        )
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        config_data[self.category_key] = self.text_input.value
        await interaction.response.send_message(f"✅ تم تحديث نص **{self.title}** بنجاح للأعضاء!", ephemeral=True)

class EmAdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تعديل المتجر 🛒", style=discord.ButtonStyle.primary, custom_id="admin_edit_shop", row=0)
    async def edit_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdminModal("shop_text", "المتجر"))

    @discord.ui.button(label="تعديل الألعاب 🎲", style=discord.ButtonStyle.secondary, custom_id="admin_edit_games", row=0)
    async def edit_games(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdminModal("games_text", "الألعاب"))

    @discord.ui.button(label="تعديل مقدمة المهام 🏆", style=discord.ButtonStyle.success, custom_id="admin_edit_tasks", row=1)
    async def edit_tasks(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdminModal("tasks_main_text", "مقدمة المهام"))

    @discord.ui.button(label="تعديل مهام الوظيفة 💼", style=discord.ButtonStyle.danger, custom_id="admin_edit_job_tasks", row=1)
    async def edit_job_tasks(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdminModal("job_tasks_text", "مهام الوظيفة"))

# ─── لوحة تصفير اقتصاد السيرفر (الجميع) ──────────────────────────────────────────
class ResetAllView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تصفير مكس توكن 🪙", style=discord.ButtonStyle.danger, custom_id="reset_all_tokens")
    async def reset_tokens(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        for user_id in data:
            data[user_id]["balance"] = 0
        save_data(data)
        await interaction.response.edit_message(content="🪙 تم بنجاح تصفير **مكس توكن** لجميع أعضاء السيرفر!", view=None)

    @discord.ui.button(label="تصفير التذاكر 🎟️", style=discord.ButtonStyle.danger, custom_id="reset_all_tickets")
    async def reset_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        for user_id in data:
            data[user_id]["tickets"] = 0
        save_data(data)
        await interaction.response.edit_message(content="🎟️ تم بنجاح تصفير **التذاكر** لجميع أعضاء السيرفر!", view=None)

# ─── لوحة تصفير العضو المحدد (مكس توكن / تذاكر / قمع) ───────────────────────────
class ResetSingleMemberView(discord.ui.View):
    def __init__(self, target_member: discord.Member):
        super().__init__(timeout=None)
        self.target_member = target_member

    @discord.ui.button(label="مكس توكن 🪙", style=discord.ButtonStyle.danger, custom_id="reset_member_tokens")
    async def reset_member_tokens(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        tid = str(self.target_member.id)
        if tid in data:
            data[tid]["balance"] = 0
            save_data(data)
            await interaction.response.edit_message(content=f"🪙 تم تصفير **مكس توكن** فقط للعضو {self.target_member.mention} بنجاح!", view=None)
        else:
            await interaction.response.edit_message(content="❌ هذا العضو لا يملك بيانات مسجلة في البوت.", view=None)

    @discord.ui.button(label="تذاكر 🎟️", style=discord.ButtonStyle.danger, custom_id="reset_member_tickets")
    async def reset_member_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        tid = str(self.target_member.id)
        if tid in data:
            data[tid]["tickets"] = 0
            save_data(data)
            await interaction.response.edit_message(content=f"🎟️ تم تصفير **التذاكر** فقط للعضو {self.target_member.mention} بنجاح!", view=None)
        else:
            await interaction.response.edit_message(content="❌ هذا العضو لا يملك بيانات مسجلة في البوت.", view=None)

    @discord.ui.button(label="قمع ☠️", style=discord.ButtonStyle.primary, custom_id="reset_member_absolute")
    async def reset_member_absolute(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        tid = str(self.target_member.id)
        if tid in data:
            data[tid]["balance"] = 0
            data[tid]["tickets"] = 0
            save_data(data)
            await interaction.response.edit_message(content=f"☠️ **تم تفعيل القمع!** تم تصفير العملات والتذاكر بالكامل للعضو {self.target_member.mention}.", view=None)
        else:
            await interaction.response.edit_message(content="❌ هذا العضو لا يملك بيانات مسجلة في البوت.", view=None)

# ─── واجهة الأزرار الأساسية لأمر إدارة الاقتصاد ──────────────────────────────────
class EconomyControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تصفير الجميع ⚠️", style=discord.ButtonStyle.danger, custom_id="eco_reset_everyone")
    async def reset_everyone_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ResetAllView()
        await interaction.response.edit_message(content="الرجاء اختيار الفئة المراد تصفيرها للجميع:", view=view)

# ─── الأوامر المائلة (Slash Commands) ──────────────────────────────────────────

@bot.tree.command(name="مكس", description="🎯 فتح القائمة الرئيسية لسيرفر MIIX GAMES")
async def miix_menu_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎯 القائمة الرئيسية - MIIX GAMES",
        description="مرحباً بك في لوحة تحكم ألعابك وحسابك. اختر من الأزرار في الأسفل للتحكم:",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=MiixMenu(), ephemeral=True)

@bot.tree.command(name="em", description="⚙️ لوحة تحكم الإدارة")
async def em_admin_cmd(interaction: discord.Interaction):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ عذراً! لا تملك صلاحية الإدارة العليا.", ephemeral=True)
        return

    embed = discord.Embed(
        title="⚙️ لوحة إدارة MIIX GAMES",
        description="اضغط على أي زر لتعديل الرسائل والنصوص المخصصة للأعضاء فوراً:",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, view=EmAdminView(), ephemeral=True)

@bot.tree.command(name="ادارة_الاقتصاد", description="📊 لوحة تحكم إدارة اقتصاد السيرفر والتصفير")
@app_commands.describe(العضو="اختر العضو المراد تصفير حساباتهم الفردية")
async def economy_admin_cmd(interaction: discord.Interaction, العضو: discord.Member = None):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ عذراً! لا تملك الصلاحيات الكافية للتحكم بالاقتصاد.", ephemeral=True)
        return

    # أولاً: في حال تم اختيار منشن عضو معين (تصفير نجم بأوبشنات محددة)
    if العضو:
        view = ResetSingleMemberView(target_member=العضو)
        await interaction.response.send_message(
            f"⚙️ تم تحديد العضو {العضو.mention}.\nالرجاء اختيار نوع التصفير المطلوب من الأزرار بالأسفل:", 
            view=view, 
            ephemeral=True
        )
        return

    # ثانياً: في حال لم يتم المنشن، يفتح لوحة تصفير الجميع المعتادة
    view = EconomyControlView()
    await interaction.response.send_message("📊 **لوحة إدارة اقتصاد السيرفر:**\nإضغط على الزر بالأسفل للبدء بعملية تصفير السيرفر بالكامل.", view=view, ephemeral=True)

@bot.tree.command(name="انجاز_مهمة", description="👑 إدارة: إنجاز مهمة معينة لعضو يدويًا ببرقم المهمة")
async def complete_task_cmd(interaction: discord.Interaction, العضو: discord.Member, رقم_المهمة: int):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ عذراً! لا تملك الصلاحيات الإدارية المطلوبة لاستخدام هذا الأمر.", ephemeral=True)
        return

    if رقم_المهمة not in TASKS_LIST:
        await interaction.response.send_message(f"❌ رقم المهمة غير صحيح! الأرقام المتاحة حالياً هي فقط: {list(TASKS_LIST.keys())}", ephemeral=True)
        return

    data = load_data()
    target_id = str(العضو.id)
    data = setup_user_data(data, target_id)

    if رقم_المهمة in data[target_id]["completed_tasks"]:
        await interaction.response.send_message(f"❌ العضو {العضو.mention} قد أنجز المهمة رقم **{رقم_المهمة}** مسبقاً ولديه علامة الصح عليها!", ephemeral=True)
        return

    data[target_id]["completed_tasks"].append(رقم_المهمة)
    data[target_id]["balance"] += TASK_REWARD
    save_data(data)

    await interaction.response.send_message(
        f"✅ تم بنجاح إنجاز المهمة رقم **{رقم_المهمة}** ({TASKS_LIST[رقم_المهمة]}) يدوياً للعضو {العضو.mention}!\n"
        f"🪙 تم منحه مكافأة الإتمام: **{TASK_REWARD}** {COIN_STR}."
    )

# ─── أوامر التحكم بالعملات وتوزيع التذاكر (المشرفين) ───────────────────────────

@bot.tree.command(name="اعطي", description="💰 منح عملات توكن لعضو محدد")
async def give_money_cmd(interaction: discord.Interaction, العضو: discord.Member, الكمية: int):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ عذراً لا تملك صلاحية.", ephemeral=True)
        return
    if الكمية <= 0: return await interaction.response.send_message("❌ الكمية أكبر من صفر!", ephemeral=True)
    data = load_data()
    tid = str(العضو.id)
    data = setup_user_data(data, tid)
    data[tid]["balance"] += الكمية
    save_data(data)
    await interaction.response.send_message(f"✅ تم إضافة **{الكمية}** {COIN_STR} إلى حساب {العضو.mention}.")

@bot.tree.command(name="اسحب", description="📉 سحب عملات توكن من عضو محدد")
async def take_money_cmd(interaction: discord.Interaction, العضو: discord.Member, الكمية: int):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ عذراً لا تملك صلاحية.", ephemeral=True)
        return
    if الكمية <= 0: return await interaction.response.send_message("❌ الكمية أكبر من صفر!", ephemeral=True)
    data = load_data()
    tid = str(العضو.id)
    data = setup_user_data(data, tid)
    if data[tid]["balance"] <= 0: return await interaction.response.send_message("❌ الحساب فارغ!", ephemeral=True)
    if data[tid]["balance"] < الكمية: الكمية = data[tid]["balance"]
    data[tid]["balance"] -= الكمية
    save_data(data)
    await interaction.response.send_message(f"✅ تم خصم **{الكمية}** {COIN_STR} من حساب {العضو.mention}.")

@bot.tree.command(name="اعطي_تذاكر", description="🎟️ منح تذاكر عادية لعضو محدد")
async def give_tickets_cmd(interaction: discord.Interaction, العضو: discord.Member, الكمية: int):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ لا تملك الصلاحيات الكافية.", ephemeral=True)
        return
    if الكمية <= 0: return await interaction.response.send_message("❌ الكمية أكبر من صفر!", ephemeral=True)
    data = load_data()
    tid = str(العضو.id)
    data = setup_user_data(data, tid)
    data[tid]["tickets"] += الكمية
    save_data(data)
    await interaction.response.send_message(f"🎟️ تم منح **{الكمية}** {TICKET_STR} إلى حساب {العضو.mention}!")

@bot.tree.command(name="اسحب_تذاكر", description="📉 سحب تذاكر عادية من عضو محدد")
async def take_tickets_cmd(interaction: discord.Interaction, العضو: discord.Member, الكمية: int):
    bot_top_role = interaction.guild.me.top_role
    if interaction.user.top_role < bot_top_role and interaction.user != interaction.guild.owner:
        await interaction.response.send_message("❌ لا تملك الصلاحيات.", ephemeral=True)
        return
    if الكمية <= 0: return await interaction.response.send_message("❌ الكمية أكبر من صفر!", ephemeral=True)
    data = load_data()
    tid = str(العضو.id)
    data = setup_user_data(data, tid)
    if data[tid]["tickets"] <= 0: return await interaction.response.send_message("❌ لا يملك تذاكر!", ephemeral=True)
    if data[tid]["tickets"] < الكمية: الكمية = data[tid]["tickets"]
    data[tid]["tickets"] -= الكمية
    save_data(data)
    await interaction.response.send_message(f"✅ تم سحب **{الكمية}** {TICKET_STR} من حساب {العضو.mention}.")

# ─── الأحداث والتشغيل ─────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    global COIN_STR, TICKET_STR
    bot.add_view(MiixMenu())
    bot.add_view(BackView())
    bot.add_view(EmAdminView())
    bot.add_view(ProfileSubMenu())
    bot.add_view(StorageView())
    bot.add_view(TasksView())
    bot.add_view(EconomyControlView())
    bot.add_view(ResetAllView())

    # إيموجي مكس توكن التلقائي
    try:
        with open(COIN_IMG, "rb") as f:
            coin_bytes = f.read()
        for guild in bot.guilds:
            existing = discord.utils.get(guild.emojis, name="mx_token")
            if existing:
                COIN_STR = f"<:mx_token:{existing.id}>"
            else:
                emoji = await guild.create_custom_emoji(name="mx_token", image=coin_bytes)
                COIN_STR = f"<:mx_token:{emoji.id}>"
    except Exception as e:
        print(f"تنبيه بخصوص الإيموجي: {e}")

    # إيموجي التذكرة الخضراء التلقائي
    try:
        with open(TICKET_IMG, "rb") as f:
            ticket_bytes = f.read()
        for guild in bot.guilds:
            existing_ticket = discord.utils.get(guild.emojis, name="mx_ticket")
            if existing_ticket:
                TICKET_STR = f"<:mx_ticket:{existing_ticket.id}>"
            else:
                emoji_ticket = await guild.create_custom_emoji(name="mx_ticket", image=ticket_bytes)
                TICKET_STR = f"<:mx_ticket:{emoji_ticket.id}>"
    except Exception as e:
        print(f"تنبيه بخصوص إيموجي التذكرة الخضراء: {e}")

    try: 
        synced = await bot.tree.sync() 
        print(f"🤖 تم تشغيل البوت بنجاح ومزامنة {len(synced)} أمر مائل!") 
    except Exception as e: 
        print(f"فشل المزامنة: {e}")

if not TOKEN:
    raise RuntimeError("لم يتم العثور على التوكن السري في ملف .env")

bot.run(TOKEN)
