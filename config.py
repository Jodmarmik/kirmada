const ADMIN_IDS = [1721894337, 1171696629];
const BOT_USERNAME = "X1PROROBOT";
const FIXED_PHOTO = "https://radare.arzfun.com/api/tg/photo?id=AgACAgUAAxkBAAED1L1nuVzH3fPVx7qYjlwPC8eeaxIpYAACN8UxG4ylyFVvS4_57ebJFwEAAwIAA3gAAzYE";
const CHANNEL_USERNAME = "NlTRIDE";
const RESULTS_PER_PAGE = 10;

function escapeMarkdown(text) {
    return text.replace(/([_*\[\]()~`>#+\-=|{}.!\\])/g, "\\$1");
}

async function extractMovieName(caption) {
    return caption.replace(/@\w+|https?:\/\/t\.me\/\S+|\[.*?\]|\(.*?\)|\d{3,4}p|WEB-DL|AAC|x264|Esub|Multi Audio|Hindi|Tamil|Telugu|Korean|BluRay|HDRip|~\w+|\.mkv|\.mp4/gi, "").trim();
}

async function sendPaginatedResults(ctx, matchingFiles, page, isEdit, searchQuery) {
    const totalFiles = matchingFiles.length;
    const totalPages = Math.ceil(totalFiles / RESULTS_PER_PAGE);
    if (totalFiles === 0) return ctx.answerCbQuery("❌ No results found.", { show_alert: true });
    if (page > totalPages) return ctx.answerCbQuery("❌ No more pages available.", { show_alert: true });

    const startIndex = (page - 1) * RESULTS_PER_PAGE;
    const paginatedFiles = matchingFiles.slice(startIndex, startIndex + RESULTS_PER_PAGE);

    const buttons = paginatedFiles.map(({ uniqueString, data }) => [
        { text: escapeMarkdown(data.caption), url: `https://t.me/${BOT_USERNAME}?start=${uniqueString}` }
    ]);

    let navButtons = [];
    if (page > 1) navButtons.push({ text: "⬅️ Previous", callback_data: `search_page_${page - 1}_${encodeURIComponent(searchQuery)}` });
    if (page < totalPages) navButtons.push({ text: "Next ➡️", callback_data: `search_page_${page + 1}_${encodeURIComponent(searchQuery)}` });
    if (navButtons.length) buttons.push(navButtons);

    const messageText = escapeMarkdown(`🔍 *Results Page ${page}/${totalPages}:*\nSelect a file below:`);

    if (isEdit) {
        ctx.editMessageText(messageText, {
            parse_mode: "MarkdownV2",
            reply_markup: { inline_keyboard: buttons }
        }).catch((err) => console.error("Error editing message:", err));
    } else {
        ctx.reply(messageText, {
            parse_mode: "MarkdownV2",
            reply_markup: { inline_keyboard: buttons }
        });
    }
}

bot.on(["video", "document"], async (ctx) => {
    if (!ADMIN_IDS.includes(ctx.from.id)) return;
    const file = ctx.message.video || ctx.message.document;
    let caption = ctx.message.caption?.toLowerCase().trim();
    if (!caption) return ctx.reply("⚠️ Please send a **video or document** with a caption.");

    caption = caption.replace(/@\w+|https?:\/\/t\.me\/\S+/gi, "").trim();
    let movieName = (await extractMovieName(caption)).toLowerCase();
    if (!movieName) return ctx.reply("⚠️ Could not extract a movie name. Use a clearer caption.");
    
    let formattedCaption = `${caption}\n\n📢 Join our channel: @${CHANNEL_USERNAME}\n🤖 Powered by @${BOT_USERNAME}`;
    let escapedCaption = escapeMarkdown(formattedCaption);
    
    let uniqueString = `file_${Date.now()}`;
    await db.operation.insertOne("files", { uniqueString, fileId: file.file_id, caption: escapedCaption, movieName });
    
    const startLink = `https://t.me/${BOT_USERNAME}?start=${uniqueString}`;
    await ctx.reply(`✅ File saved under: *${escapeMarkdown(movieName)}*\n📎 [Click here to access](${startLink})`, {
        parse_mode: "MarkdownV2",
        disable_web_page_preview: true
    });
});

bot.command("start", async (ctx) => {
    const args = ctx.message.text.split(" ").slice(1);
    const firstName = ctx.from.first_name || "User";

    if (args.length === 0) {
        await ctx.replyWithPhoto(FIXED_PHOTO, {
            caption: `<b>🎬 Welcome, ${firstName}, to Movie Search Bot! 🎬</b>\n\n🔍 <i>Instantly find any movie, TV show, or series with ease!</i>\n\n📌 <b>Join our channel for updates:</b>`,
            parse_mode: "HTML",
            reply_markup: { inline_keyboard: [[{ text: "📢 Join Channel", url: `https://t.me/${CHANNEL_USERNAME}` }]] }
        });
        return;
    }

    const uniqueString = args[0];
    const fileData = await db.operation.findOne("files", { uniqueString });
    if (!fileData) return ctx.reply("⚠️ No files found for this link.");

    let updatedCaption = `${fileData.caption}\n\n📢 Join our channel: @${CHANNEL_USERNAME}\n🤖 Powered by @${BOT_USERNAME}`;
    let escapedCaption = escapeMarkdown(updatedCaption);

    await ctx.replyWithDocument(fileData.fileId, { 
        caption: escapedCaption, 
        parse_mode: "MarkdownV2",
        reply_markup: { inline_keyboard: [[{ text: "📢 Join Channel", url: `https://t.me/${CHANNEL_USERNAME}` }]] }
    });
});

bot.on("text", async (ctx) => {
    const query = ctx.message.text.toLowerCase().trim();
    let matchingFiles = await db.operation.findAll("files", { movieName: { $regex: query, $options: "i" } });
    matchingFiles = matchingFiles.map(file => ({ uniqueString: file.uniqueString, data: file }));
    if (matchingFiles.length === 0) {
        return ctx.reply(escapeMarkdown("❌ *Movie Not Found!*\n\n🔍 Please check your spelling and try again, or the requested movie/series might not be available in our database.\n\n📢 Stay updated with the latest uploads by joining our channel!"), {
            parse_mode: "MarkdownV2",
            reply_markup: { inline_keyboard: [[{ text: "📢 Join Channel", url: "https://t.me/+UvTc24tytmQ5MmU1" }]] }
        });
    }
    sendPaginatedResults(ctx, matchingFiles, 1, false, query);
});

bot.on("callback_query", async (ctx) => {
    const queryData = ctx.callbackQuery.data;
    if (queryData.startsWith("search_page_")) {
        const parts = queryData.split("_");
        const page = parseInt(parts[2]);
        const searchQuery = decodeURIComponent(parts.slice(3).join("_"));

        if (!page || page < 1) return;

        let matchingFiles = await db.operation.findAll("files", { movieName: { $regex: searchQuery, $options: "i" } });
        matchingFiles = matchingFiles.map(file => ({ uniqueString: file.uniqueString, data: file }));

        sendPaginatedResults(ctx, matchingFiles, page, true, searchQuery);
        await ctx.answerCbQuery();
    }
});
