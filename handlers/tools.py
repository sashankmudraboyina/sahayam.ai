import ast
import datetime
import html
import operator as op
import random
from typing import Union
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Safe AST-based math evaluator
SUPPORTED_OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval_ast(node: ast.AST) -> Union[int, float]:
    """Recursively evaluate an AST expression node securely."""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.BinOp):
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        op_type = type(node.op)
        if op_type not in SUPPORTED_OPERATORS:
            raise ValueError(f"Operator {op_type.__name__} is not allowed.")
        if op_type == ast.Pow:
            # Prevent excessive exponentiation DoS
            if right > 1000 or left > 100000:
                raise ValueError("Exponent values are too large.")
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero.")
        return SUPPORTED_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_ast(node.operand)
        op_type = type(node.op)
        if op_type not in SUPPORTED_OPERATORS:
            raise ValueError(f"Unary operator {op_type.__name__} is not allowed.")
        return SUPPORTED_OPERATORS[op_type](operand)
    else:
        raise ValueError("Invalid or unsafe expression.")


def safe_calculate(expression: str) -> Union[int, float]:
    """Parses and calculates a mathematical expression securely."""
    parsed = ast.parse(expression, mode="eval")
    return _eval_ast(parsed)


def get_tools_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for the interactive tools menu."""
    keyboard = [
        [
            InlineKeyboardButton("🎲 Roll Die", callback_data="tool:roll"),
            InlineKeyboardButton("🪙 Flip Coin", callback_data="tool:flip"),
        ],
        [
            InlineKeyboardButton("🕒 Current Time", callback_data="tool:time"),
            InlineKeyboardButton("💡 Random Fact", callback_data="tool:fact"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def tools_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /tools command."""
    text = (
        "🛠 <b>Interactive Utilities Menu</b>\n\n"
        "Select a tool below or use one of the direct commands:\n"
        "• <code>/roll [sides]</code> (e.g. <code>/roll 20</code>)\n"
        "• <code>/flip</code> (Heads or Tails)\n"
        "• <code>/calc &lt;expr&gt;</code> (e.g. <code>/calc 12 * 8</code>)\n"
        "• <code>/echo &lt;text&gt;</code> (Text analysis)"
    )
    if update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=get_tools_keyboard(),
            parse_mode=ParseMode.HTML,
        )


async def roll_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /roll [sides] command."""
    sides = 6
    if context.args and len(context.args) > 0:
        try:
            val = int(context.args[0])
            if 2 <= val <= 10000:
                sides = val
            else:
                if update.message:
                    await update.message.reply_text("⚠️ Sides must be between 2 and 10,000.")
                return
        except ValueError:
            if update.message:
                await update.message.reply_text("⚠️ Please specify a valid integer for sides. Example: <code>/roll 20</code>", parse_mode=ParseMode.HTML)
            return

    result = random.randint(1, sides)
    response = f"🎲 <b>Dice Roll (1–{sides}):</b>\nYou rolled a <b>{result}</b>!"
    if update.message:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)


async def flip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /flip command."""
    outcome = random.choice(["Heads 🦅", "Tails 🪙"])
    response = f"🪙 <b>Coin Flip:</b>\nResult: <b>{outcome}</b>"
    if update.message:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)


async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /calc <expression> command."""
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "ℹ️ <b>Usage:</b> <code>/calc &lt;expression&gt;</code>\n"
                "Example: <code>/calc (15 * 4) + 2.5</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    expr_str = " ".join(context.args)
    try:
        result = safe_calculate(expr_str)
        # Format floating numbers nicely
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        safe_expr = html.escape(expr_str)
        response = f"🧮 <b>Calculation:</b>\n<code>{safe_expr}</code> = <b>{result}</b>"
    except ZeroDivisionError:
        response = "❌ <b>Error:</b> Division by zero is not allowed."
    except Exception as e:
        response = f"❌ <b>Calculation Error:</b> {html.escape(str(e))}"

    if update.message:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /time command."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_local = datetime.datetime.now()
    response = (
        "🕒 <b>Current Time:</b>\n\n"
        f"🌐 <b>UTC:</b> <code>{now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}</code>\n"
        f"🖥 <b>Server:</b> <code>{now_local.strftime('%Y-%m-%d %H:%M:%S')}</code>"
    )
    if update.message:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)


async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /echo <text> command with text analysis."""
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "ℹ️ <b>Usage:</b> <code>/echo &lt;your message&gt;</code>\n"
                "Example: <code>/echo Hello Telegram!</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    text = " ".join(context.args)
    word_count = len(text.split())
    char_count = len(text)
    safe_text = html.escape(text)

    response = (
        f"📣 <b>Echo:</b>\n{safe_text}\n\n"
        "📊 <b>Stats:</b>\n"
        f"• Characters: <b>{char_count}</b>\n"
        f"• Words: <b>{word_count}</b>\n"
        f"• Uppercase: <code>{safe_text.upper()}</code>"
    )
    if update.message:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
