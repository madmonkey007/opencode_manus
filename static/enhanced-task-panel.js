/**
 * Enhanced Task Panel - Manus-style Progressive Disclosure
 * 瀹炵幇绫讳技 Manus 鐨勯€愮骇灞曞紑浠诲姟闈㈡澘
 */

/**
 * 鉁?杈呭姪鍑芥暟 - 鎸夋椂闂存埑鎺掑簭浜嬩欢
 */
window.sortEventsByTimestamp = function (events) {
    if (!Array.isArray(events)) return [];
    return [...events].sort((a, b) => {
        const timeA = a.timestamp || (a.data && a.data.timestamp) || a.time || 0;
        const timeB = b.timestamp || (b.data && b.data.timestamp) || b.time || 0;
        return timeA - timeB;
    });
};

/**
 * 鉁?浠ｇ爜瀹℃煡淇锛氳緟鍔╁嚱鏁?- 浠庢枃浠跺璞′腑鎻愬彇鏂囦欢鍚嶅拰鎵╁睍鍚? */
function extractFileInfo(file) {
    const fileName = typeof file === 'string' ? file : (file.name || file.path || '');
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    return { fileName, ext };
}

/**
 * 鉁?浠ｇ爜瀹℃煡淇锛氭枃浠惰矾寰勯獙璇佸嚱鏁? * 闃叉璺緞閬嶅巻鏀诲嚮锛?./../etc/passwd锛? * 淇闂锛欼mportant #1 - 缂哄皯鏂囦欢璺緞楠岃瘉
 */
function isValidFilePath(filePath) {
    // 鉁?鏂规1淇锛氬厑璁窵inux/Mac缁濆璺緞锛堝悗绔爣鍑嗚矾寰勬牸寮忥級
    // 渚嬪锛?app/opencode/workspace/ses_xxx/file.html

    // 闃绘璺緞閬嶅巻鏀诲嚮锛堝叧閿畨鍏ㄩ獙璇侊級
    if (filePath.includes('..')) {
        console.warn('[Security] Path traversal attack detected:', filePath);
        return false;
    }

    // 闃绘Windows缁濆璺緞锛圽\寮€澶达級
    if (filePath.startsWith('\\\\')) {
        console.warn('[Security] Windows absolute path not allowed:', filePath);
        return false;
    }

    // 鉁?鍏佽Linux/Mac缁濆璺緞锛?寮€澶达級- 鍚庣鏍囧噯璺緞鏍煎紡

    // 楠岃瘉璺緞鏍煎紡锛堝厑璁哥粷瀵硅矾寰勫拰鐩稿璺緞锛?    // 瑙勫垯锛氬瓧姣嶃€佹暟瀛椼€佷笅鍒掔嚎銆佺偣銆佺煭妯嚎銆佹枩鏉?    const validPattern = /^[a-zA-Z0-9_\-.\/]+\.[a-zA-Z0-9]+$/;
    const isValid = validPattern.test(filePath);

    if (!isValid) {
        console.warn('[Security] Invalid file path format:', filePath);
    }

    return isValid;
}

/**
 * 鉁?浠ｇ爜瀹℃煡淇锛氬畨鍏ㄥ湴娓叉煋Markdown鍐呭
 * 浣跨敤textContent闃叉XSS鏀诲嚮
 * 淇闂锛欳ritical #1 - marked.parse()鏈秷姣? */
function safeRenderMarkdown(markdownContent) {
    // 鈿狅笍 瀹夊叏璀﹀憡锛歮arked.parse() 杈撳嚭鍖呭惈鐢ㄦ埛鍐呭锛屽繀椤绘秷姣掞紒
    // 鎺ㄨ崘鏂规锛氬畨瑁呭苟浣跨敤DOMPurify
    //   npm install dompurify
    //   import DOMPurify from 'dompurify';
    //   return DOMPurify.sanitize(marked.parse(markdownContent));
    //
    // 鉁?v=38.4.11 鏀硅繘锛氫娇鐢ㄧ畝鍖栫殑markdown娓叉煋鍣?    // 鏀寔甯歌鏍煎紡锛?*绮椾綋**銆?鏂滀綋*銆? 鍒楄〃銆乣浠ｇ爜`銆佹崲琛岀瓑
    // 瀹夊叏鎬э細鍙鐞嗙壒瀹氱殑markdown璇硶锛屼笉娓叉煋HTML鏍囩
    try {
        if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
            // 鐢熶骇鐜锛氫娇鐢―OMPurify娑堟瘨
            return DOMPurify.sanitize(marked.parse(markdownContent));
        } else {
            // 鉁?v=38.4.11: 绠€鍖栫殑markdown娓叉煋鍣紙瀹夊叏涓旀敮鎸佸熀鏈牸寮忥級
            return renderSimpleMarkdown(markdownContent);
        }
    } catch (e) {
        console.error('[safeRenderMarkdown] Failed to render markdown:', e);
        const div = document.createElement('div');
        div.textContent = markdownContent;
        return div.innerHTML;
    }
}

/**
 * 鉁?v=38.4.11: 绠€鍖栫殑markdown娓叉煋鍣? * 鏀寔鍩烘湰markdown璇硶锛屽悓鏃朵繚璇乆SS瀹夊叏
 * 涓嶄娇鐢╡val/innerHTML锛屾墜鍔ㄦ瀯寤篋OM
 */
function renderSimpleMarkdown(text) {
    if (!text) return '';

    // 瀹夊叏澶勭悊锛氬厛杞箟HTML鐗规畩瀛楃
    let safeText = escapeHtml(text);

    // 鉁?浼樺寲1锛氱Щ闄ょ粺璁′俊鎭锛堝畬鎴愰樁娈点€佸伐鍏疯皟鐢ㄣ€佷换鍔″畬鎴愮瓑锛?    // 鍖归厤鍚勭鏍煎紡鐨勭粺璁′俊鎭锛堝寘鎷甫emoji鐨勶級
    safeText = safeText.replace(/^[\s]*[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾*[\s]*浠诲姟瀹屾垚.*$/gm, '');
    safeText = safeText.replace(/^[\s]*浠诲姟瀹屾垚.*$/gm, '');
    safeText = safeText.replace(/^[\s]*(瀹屾垚闃舵|闃舵|闃舵瀹屾垚|瀹屾垚).*[:锛歖.*$/gm, '');
    safeText = safeText.replace(/^[\s]*宸ュ叿璋冪敤.*[:锛歖.*$/gm, '');
    safeText = safeText.replace(/^[\s]*\*.*瀹屾垚闃舵.*$/gm, '');
    safeText = safeText.replace(/^[\s]*\*.*宸ュ叿璋冪敤.*$/gm, '');
    // 鉁?绉婚櫎鍒楄〃椤规牸寮忕殑缁熻淇℃伅
    safeText = safeText.replace(/^[\s]*-\s*[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾*[\s]*(瀹屾垚闃舵|闃舵|浠诲姟瀹屾垚).*[:锛歖?.*$/gm, '');
    safeText = safeText.replace(/^[\s]*-\s*(瀹屾垚闃舵|闃舵).*[:锛歖.*$/gm, '');
    safeText = safeText.replace(/^[\s]*-\s*宸ュ叿璋冪敤.*[:锛歖.*$/gm, '');
    safeText = safeText.replace(/^[\s]*鈥s*[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾*[\s]*(瀹屾垚闃舵|闃舵|浠诲姟瀹屾垚).*[:锛歖?.*$/gm, '');
    safeText = safeText.replace(/^[\s]*鈥s*(瀹屾垚闃舵|闃舵).*[:锛歖.*$/gm, '');
    safeText = safeText.replace(/^[\s]*鈥s*宸ュ叿璋冪敤.*[:锛歖.*$/gm, '');

    // 鉁?浼樺寲2锛氱Щ闄moji锛堝寘鎷甫 鉁?绛夋爣璁扮殑琛岋級
    // 绉婚櫎琛岄鐨別moji鍜屾爣璁帮紙濡?鉁呫€佲潓銆佲殸锔?绛夛級
    safeText = safeText.replace(/^[\s]*[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾+[\s]*/gm, '');
    // 绉婚櫎琛屼腑鐨別moji
    safeText = safeText.replace(/[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾/g, '');

    // 鐒跺悗澶勭悊markdown璇硶锛堜粠鐗规畩鍒颁竴鑸紝閬垮厤閲嶅澶勭悊锛?    // 1. 浠ｇ爜鍧?```code```
    safeText = safeText.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 dark:bg-zinc-800 p-2 rounded my-2 overflow-x-auto text-xs"><code>$1</code></pre>');

    // 2. 琛屽唴浠ｇ爜 `code`
    safeText = safeText.replace(/`([^`]+)`/g, '<code class="bg-gray-100 dark:bg-zinc-800 px-1 rounded text-xs">$1</code>');

    // 3. 绮椾綋 **text**
    safeText = safeText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 4. 鏂滀綋 *text*
    safeText = safeText.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 5. 閾炬帴 [text](url)
    safeText = safeText.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-500 underline" target="_blank" rel="noopener">$1</a>');

    // 鉁?浼樺寲3锛氬鐞嗗垎闅旂 --- 浣滀负娈佃惤鍒嗛殧锛堟崲琛屾樉绀猴級
    safeText = safeText.replace(/^---+$/gm, '<hr class="my-2 border-gray-300 dark:border-zinc-700">');

    // 鉁?浼樺寲4锛氭敼杩涙棤搴忓垪琛ㄥ鐞?- 姣忎釜鍒楄〃椤瑰崟鐙垚琛?    // 鍖归厤杩炵画鐨勫垪琛ㄩ」锛屽苟涓烘瘡涓垱寤虹嫭绔嬬殑娈佃惤
    const listPattern = /(^|\n)- (.+?)(?=\n- |\n\n|\n\d+\. |\n*$)/g;
    safeText = safeText.replace(listPattern, (match, prefix, itemContent) => {
        // 绉婚櫎鍒楄〃椤逛腑鐨別moji
        const cleanContent = itemContent.replace(/^[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾+[\s]*/, '');
        return `<div class="flex items-start gap-2 my-2"><span class="text-gray-400 dark:text-gray-600 mt-0.5">鈥?/span><span>${cleanContent}</span></div>`;
    });

    // 鉁?浼樺寲5锛氭敼杩涙湁搴忓垪琛ㄥ鐞?- 姣忎釜鍒楄〃椤瑰崟鐙垚琛?    const orderedListPattern = /(^|\n)(\d+)\. (.+?)(?=\n\d+\. |\n\n|\n- |\n*$)/g;
    safeText = safeText.replace(orderedListPattern, (match, prefix, num, itemContent) => {
        const cleanContent = itemContent.replace(/^[鉁呪潓鈿狅笍馃敡馃摑馃挕馃幆馃搳猸怾+[\s]*/, '');
        return `<div class="flex items-start gap-2 my-2"><span class="text-gray-400 dark:text-gray-600 mt-0.5 font-semibold">${num}.</span><span>${cleanContent}</span></div>`;
    });

    // 6. 鏍囬 # Heading
    safeText = safeText.replace(/^### (.+)$/gm, '<h3 class="text-sm font-bold my-2">$1</h3>');
    safeText = safeText.replace(/^## (.+)$/gm, '<h2 class="text-base font-bold my-2">$1</h2>');
    safeText = safeText.replace(/^# (.+)$/gm, '<h1 class="text-lg font-bold my-2">$1</h1>');

    // 7. 鎹㈣锛堜笉鍦ㄥ垪琛ㄤ腑鐨勬崲琛岋級
    // 浣跨敤 /\n{2,}/g 鍖归厤2涓垨鏇村杩炵画鎹㈣绗?    safeText = safeText.replace(/\n{2,}/g, '<br class="mb-3">');

    // 8. 鍗曚釜鎹㈣杞崲涓?br>
    safeText = safeText.replace(/\n/g, '<br>');

    return safeText;
}

// 娓叉煋澧炲己鐨勪换鍔￠潰鏉?function renderEnhancedTaskPanel(session) {
    const container = document.createElement('div');
    container.className = 'enhanced-task-panel space-y-6';

    const pSep = '\n\n---\n\n';
    const rSep = '\n\n---\n\n**鏂扮殑鍥炵瓟锛?*\n\n';

    // 鍒嗗壊澶氳疆瀵硅瘽
    const prompts = (session.prompt || '').split(pSep);
    const responses = (session.response || '').split(rSep);

    const turnsCount = Math.max(prompts.length, responses.length);

    // 鉁?v=36浼樺寲锛氶璁＄畻deliverables鎸塼urn_index鍒嗙粍锛堝彧鎵ц涓€娆★級
    // 鎬ц兘锛歄(n)鎬诲鏉傚害锛寁s 鍘熸柟妗堢殑O(n * turnsCount)
    // 閬垮厤锛氭瘡涓€杞兘filter鎵€鏈塪eliverables
    const deliverablesByTurn = {};
    if (session.deliverables && session.deliverables.length > 0) {
        session.deliverables.forEach(d => {
            // 鍏煎鏂版棫鏍煎紡锛?            // - 鏂版牸寮忥細{ path: '/app/file.html', turn_index: 1, timestamp: ... }
            // - 鏃ф牸寮忥細'/app/file.html'
            const path = typeof d === 'string' ? d : (d.path || d);
            const turn = typeof d === 'object' && d.turn_index ? d.turn_index : 1;

            if (!deliverablesByTurn[turn]) {
                deliverablesByTurn[turn] = [];
            }
            deliverablesByTurn[turn].push(path);
        });
    }

    for (let i = 0; i < turnsCount; i++) {
        const turnContainer = document.createElement('div');
        turnContainer.className = `conversation-turn space-y-4 ${i < turnsCount - 1 ? 'border-b border-gray-100 dark:border-zinc-800 pb-8' : ''}`;

        // 1. 璇ヨ疆鐨勭敤鎴疯緭鍏?        if (prompts[i]) {
            const userCard = createUserPromptCard(prompts[i]);
            turnContainer.appendChild(userCard);
        }

        // 2. 浠诲姟闃舵鍗＄墖
        const turnPhases = session.phases ? session.phases.filter(p => {
            const phaseTurn = parseInt(p.turn_index, 10);
            return phaseTurn === i + 1;
        }) : [];

        // 鍏滃簳锛氭渶鍚庝竴杞笖娌℃湁鍖归厤 turn_index 鏃讹紝鏄剧ず鎵€鏈?phases锛堝惈鍘嗗彶鎭㈠鐨勬棤 turn_index phases锛?        if (i === turnsCount - 1 && turnPhases.length === 0 && session.phases && session.phases.length > 0) {
            const unassociatedPhases = session.phases.filter(p => {
                const phaseTurn = parseInt(p.turn_index, 10);
                return !p.turn_index || isNaN(phaseTurn);
            });
            // 鉁?鍘嗗彶鎭㈠鍏滃簳锛氬鏋滄墍鏈?phases 閮芥病鏈?turn_index锛屽叏閮ㄦ樉绀?            const phasesToShow = unassociatedPhases; //  修复：只显示无turn_index的phases，不fallback到所有phases（避免追问时旧phases闪现）
            if (phasesToShow.length > 0) {
                const phasesCard = createPhasesCard(phasesToShow, session.currentPhase);
                turnContainer.appendChild(phasesCard);
            }
        } else if (turnPhases.length > 0) {
            const phasesCard = createPhasesCard(turnPhases, session.currentPhase);
            turnContainer.appendChild(phasesCard);
        }

        // 2b. thoughtEvents锛堝巻鍙叉仮澶嶆椂 thought 涓嶅湪 phase.events 閲岋級
        // 鍙湪鏈€鍚庝竴杞彃鍏ワ紝閬垮厤澶氳疆瀵硅瘽閲嶅鏄剧ず
        // 鍖呰繘浼?phase 鍗＄墖锛屾牱寮忎笌鐪熷疄 phase 涓€鑷达紙鍏滃簳锛歱hases 涓虹┖鏃朵篃鑳芥樉绀猴級
        // 鉁?淇锛氬鏋減hase.events涓凡鏈塼hought锛屼笉鏄剧ずthoughtEvents閬垮厤閲嶅
        const hasThoughtInPhases = turnPhases && turnPhases.some(p =>
            p.events && p.events.some(e => e.type === 'thought')
        );

        if (i === turnsCount - 1 && session.thoughtEvents && session.thoughtEvents.length > 0 && !hasThoughtInPhases) {
            const thoughtEvents = session.thoughtEvents.map(ev => ({
                type: 'thought',
                content: ev.content || ev.data?.text || '',
                id: ev.id
            })).filter(ev => ev.content);
            if (thoughtEvents.length > 0) {
                const thoughtPhaseCard = createPhasesCard([{
                    id: '_thought_pseudo_phase',
                    title: '鎬濊€冭繃绋?,
                    status: 'done',
                    events: thoughtEvents
                }], null);
                turnContainer.appendChild(thoughtPhaseCard);
            }
        }

        // 3. 璇ヨ疆鐨勫洖绛斿拰浜や粯鐗?
        // 鉁?v=37浼樺寲锛氫粠棰勮绠楃殑Map涓幏鍙栧綋鍓嶈疆娆＄殑deliverables锛圤(1)锛?        const turnDeliverables = deliverablesByTurn[i + 1] || [];

        // 鉁?v=37淇锛氭洿鍋ュ．鐨勬覆鏌撴潯浠?        // 闂锛氳拷闂椂response鍙兘涓虹┖锛屽鑷翠氦浠橀潰鏉夸笉鏄剧ず
        // 瑙ｅ喅锛氭弧瓒充互涓嬩换涓€鏉′欢灏辨覆鏌擄細
        //   1. 鏈塺esponse鍐呭锛屾垨
        //   2. 鏄渶鍚庝竴杞紝鎴?        //   3. 鏈夎杞殑deliverables锛堝嵆浣縭esponse涓虹┖锛?        const hasResponse = responses[i] && responses[i].trim();
        const isLastTurn = i === turnsCount - 1;
        const hasDeliverables = turnDeliverables && turnDeliverables.length > 0;

        // 璋冭瘯鏃ュ織
        console.log('[Render] Turn', i + 1, 'conditions:', {
            hasResponse,
            isLastTurn,
            hasDeliverables,
            deliverablesCount: turnDeliverables.length,
            willRender: hasResponse || isLastTurn || hasDeliverables
        });

        if (responses[i] !== undefined && responses[i] !== null) {
            if (hasResponse || isLastTurn || hasDeliverables) {
                const summaryCard = createDeliverableCard({
                    ...session,
                    response: responses[i] || '',  // 鉁?纭繚response涓嶄负undefined
                    // 鉁?v=37淇锛氭瘡杞彧鏄剧ず璇ヨ疆鐢熸垚鐨勪氦浠樼墿锛屼笉鏄剧ず鍏朵粬杞殑
                    // 浣跨敤棰勮绠桵ap锛屾€ц兘浼樺寲锛歄(1)鏌ヨ vs O(n) filter
                    deliverables: turnDeliverables
                });
                turnContainer.appendChild(summaryCard);
            }
        }

        container.appendChild(turnContainer);
    }

    return container;
}

// 鍒涘缓鐢ㄦ埛杈撳叆鍗＄墖
function createUserPromptCard(prompt) {
    const card = document.createElement('div');
    card.className = 'message-bubble user-bubble text-sm';
    card.style.cssText = 'margin-left: auto; margin-right: 0; width: fit-content; max-width: 85%;';
    card.textContent = prompt;
    return card;
}

// 鍒涘缓闃舵鍗＄墖锛堥€愮骇灞曞紑锛?function createPhasesCard(phases, currentPhaseId) {
    const card = document.createElement('div');
    card.className = 'overflow-hidden'; // 鍘绘帀鑳屾櫙銆佽竟妗嗗拰闃村奖

    const header = document.createElement('div');
    header.className = 'px-4 py-3 border-b border-border-light dark:border-border-dark bg-gray-50 dark:bg-zinc-800/50 flex items-center justify-between cursor-pointer hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors';
    header.innerHTML = `
        <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-purple-500 text-[20px]">account_tree</span>
            <span class="text-sm font-semibold text-gray-900 dark:text-white">浠诲姟闃舵</span>
            <span class="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-full font-medium">${phases.length} 涓樁娈?/span>
        </div>
        <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200">expand_more</span>
    `;

    const body = document.createElement('div');
    body.className = 'phases-body py-2 space-y-3 relative'; // 绉婚櫎 p-4 鍑忓皯澶栭儴杈硅窛

    // 鍏堝垱寤烘墍鏈?phase
    const phaseItems = [];
    phases.forEach((phase, idx) => {
        const isLast = idx === phases.length - 1;
        const phaseItem = createPhaseItem(phase, idx, currentPhaseId, isLast);
        phaseItems.push(phaseItem);
        body.appendChild(phaseItem);
    });

    // 娣诲姞璐┛鎵€鏈?phase 鐨勮繛缁疄绾?    // 浠庣涓€涓?phase 鐨勭姸鎬佸浘鏍囦腑蹇冨紑濮嬶紝鍒版渶鍚庝竴涓?phase 鐨勭姸鎬佸浘鏍囦腑蹇?    if (phases.length > 1) {
        const timelineLine = document.createElement('div');
        timelineLine.className = 'absolute bg-gray-300 dark:bg-gray-600 opacity-50';
        // 24px = 12px (header padding-left) + 12px (鍥炬爣鍗婂緞)
        // 32px = 8px (body padding-top) + 12px (header padding-top) + 12px (鍥炬爣涓績鍋忕Щ)
        timelineLine.style.cssText = 'left: 24px; width: 2px; top: 32px; bottom: 32px; z-index: 0;';
        body.appendChild(timelineLine);
    }

    card.appendChild(body);

    return card;
}

// 鍒涘缓鍗曚釜闃舵椤癸紙鍖呭惈宓屽鐨勬墽琛屽姩浣滐級
function createPhaseItem(phase, index, currentPhaseId, isLast) {
    const item = document.createElement('div');
    item.className = 'phase-item';
    const isActive = phase.id === currentPhaseId;
    const isDone = phase.status === 'done' || phase.status === 'completed';
    const isPending = !isActive && !isDone;

    // 璁＄畻璇ラ樁娈电殑浜嬩欢鏁伴噺
    const eventCount = phase.events ? phase.events.length : 0;

    // 鐘舵€佸浘鏍?HTML
    let statusIconHtml, statusClass, statusBg;
    if (isDone) {
        // 瀹屾垚鐘舵€侊細榛戣壊鍦嗗舰 + 鐧借壊鍕鹃€?SVG
        statusIconHtml = `<svg width="12" height="12" color="white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        statusClass = 'bg-gray-800 dark:bg-gray-700';
        statusBg = 'bg-gray-50 dark:bg-gray-900/20';
    } else {
        // 鎵ц涓垨鏈紑濮嬶細鐏拌壊 loading 鍦嗗湀
        statusIconHtml = `<svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="32" stroke-dashoffset="32" class="text-gray-300 opacity-25"></circle>
            <path d="M12 2C17.5228 2 22 6.47715 22 12" stroke="currentColor" stroke-width="3" stroke-linecap="round" class="text-gray-500"></path>
        </svg>`;
        statusClass = 'bg-white dark:bg-zinc-800';
        statusBg = isActive ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-zinc-800/50';
    }

    // 闃舵澶撮儴
    const header = document.createElement('div');
    header.className = `phase-header ${statusBg} rounded-xl p-3 transition-all duration-200 cursor-pointer hover:shadow-sm relative`;

    header.innerHTML = `
        <div class="flex items-center gap-3">
            <!-- 鐘舵€佸浘鏍囧鍣?-->
            <div class="flex items-center justify-center w-6 h-6 rounded-full ${statusClass} flex-shrink-0 relative" style="z-index: 10;">
                ${statusIconHtml}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 dark:text-white">${index + 1}. ${escapeHtml(phase.title)}</span>
                    ${eventCount > 0 ? `<span class="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full font-medium">${eventCount} 涓姩浣?/span>` : ''}
                </div>
                ${phase.description ? `<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">${escapeHtml(phase.description)}</div>` : ''}
            </div>
            ${isActive && !isDone ? '<span class="text-xs px-2 py-0.5 bg-blue-500 text-white rounded-full font-medium">杩涜涓?/span>' : ''}
            ${isDone ? '<span class="text-xs px-2 py-0.5 bg-green-500 text-white rounded-full font-medium">宸插畬鎴?/span>' : ''}
            ${eventCount > 0 ? '<span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200 text-[18px]">expand_more</span>' : ''}
        </div>
    `;

    // 闃舵鍐呭锛堟墽琛屽姩浣滃垪琛級
    const body = document.createElement('div');
    body.className = 'phase-body hidden pl-9 pr-3 pt-2 pb-2 space-y-2';

    // 娓叉煋璇ラ樁娈电殑鎵€鏈変簨浠讹紙鎵ц鍔ㄤ綔锛?    // 鉁?v=38.4.11 淇锛氫娇鐢ㄥ伐鍏峰嚱鏁版寜鏃堕棿鎴虫帓搴忥紝纭繚浜嬩欢鏄剧ず椤哄簭姝ｇ‘
    // 闂锛歋SE浜嬩欢鍒拌揪椤哄簭鍙兘涔卞簭锛屽鑷磘hought浜嬩欢鏄剧ず鍦ㄥ伐鍏疯皟鐢ㄤ箣鍚?    // 瑙ｅ喅锛氫娇鐢ㄥ叏灞€宸ュ叿鍑芥暟window.sortEventsByTimestamp鎺掑簭锛堝崌搴忥紝鏃╃殑鍦ㄥ墠锛?    if (phase.events) {
        const sortedEvents = window.sortEventsByTimestamp(phase.events);

        if (sortedEvents.length > 0) {
            sortedEvents.forEach((event, eventIdx) => {
                const eventItem = createEventItem(event, eventIdx);
                body.appendChild(eventItem);
            });
        } else if (isActive) { // 濡傛灉鏄綋鍓嶆椿鍔ㄩ樁娈典絾娌℃湁浜嬩欢
            const loadingMsg = document.createElement('div');
            loadingMsg.className = 'text-xs text-gray-400 italic py-1 px-4 ml-6';
            loadingMsg.textContent = '鍑嗗鎵ц涓?..';
            body.appendChild(loadingMsg);
        } else { // 宸插畬鎴愭垨鏈紑濮嬩絾娌℃湁浜嬩欢鐨勯樁娈?            const emptyMsg = document.createElement('div');
            emptyMsg.className = 'text-xs text-gray-400 italic py-1 px-4 ml-6';
            emptyMsg.textContent = '鏃犲叧鑱斾簨浠?;
            body.appendChild(emptyMsg);
        }
    } else {
        body.innerHTML = '<div class="text-xs text-gray-400 dark:text-gray-600 italic">鏆傛棤鎵ц鍔ㄤ綔</div>';
    }

    // 鐐瑰嚮灞曞紑/鏀惰捣鍔ㄤ綔鍒楄〃
    if (eventCount > 0) {
        header.onclick = () => {
            const isHidden = body.classList.contains('hidden');
            body.classList.toggle('hidden');
            const expandIcon = header.querySelector('.expand-icon');
            if (expandIcon) {
                expandIcon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        };

        // 濡傛灉鏄綋鍓嶆椿鍔ㄩ樁娈垫垨宸插畬鎴愰樁娈碉紝榛樿灞曞紑
        if (isActive || isDone) {
            body.classList.remove('hidden');
            const expandIcon = header.querySelector('.expand-icon');
            if (expandIcon) {
                expandIcon.style.transform = 'rotate(180deg)';
            }
        }
    }

    item.appendChild(header);
    item.appendChild(body);

    return item;
}

// 杈呭姪鍑芥暟锛氫粠宸ュ叿杈撳叆涓彁鍙栨湁鎰忎箟鐨勬憳瑕?function getToolSummary(toolType, input, output) {
    const tool = toolType.toLowerCase();

    // === 鍩虹鏂囦欢鎿嶄綔 ===
    if (tool === 'read') {
        const path = input.path || input.file_path || input.file;
        return path ? `璇诲彇鏂囦欢: ${path}` : '璇诲彇鏂囦欢';
    }

    if (tool === 'write') {
        const path = input.path || input.file_path || input.file;
        const contentLen = input.content ? input.content.length : 0;
        return path ? `鍐欏叆鏂囦欢: ${path} (${contentLen} 瀛楃)` : '鍐欏叆鏂囦欢';
    }

    if (tool === 'edit' || tool === 'file_editor') {
        const path = input.path || input.file_path || input.file;
        return path ? `缂栬緫鏂囦欢: ${path}` : '缂栬緫鏂囦欢';
    }

    // === 鍛戒护琛屽伐鍏?===
    if (tool === 'bash' || tool === 'terminal' || tool === 'execute') {
        const cmd = input.command || input.cmd;
        return cmd ? `鎵ц鍛戒护: ${cmd}` : '鎵ц鍛戒护';
    }

    if (tool === 'grep') {
        const pattern = input.pattern || input.regex || input.search;
        const path = input.path || input.file_path || input.file;
        if (pattern && path) {
            return `鎼滅储: ${pattern} 鍦?${path}`;
        }
        return pattern ? `鎼滅储: ${pattern}` : '鎼滅储';
    }

    // === 瀛恆gent宸ュ叿 ===
    if (tool === 'subagent_explore' || tool === 'explore') {
        const query = input.query || input.description || input.task;
        return query ? `鎺㈢储: ${query}` : '鎺㈢储浠诲姟';
    }

    if (tool === 'subagent_coder' || tool === 'coder') {
        const task = input.task || input.description || input.instruction;
        return task ? `浠ｇ爜鐢熸垚: ${task}` : '浠ｇ爜鐢熸垚';
    }

    if (tool === 'subagent_delegate' || tool === 'delegate_task') {
        const category = input.category || input.subagent_type;
        const task = input.task || input.description;
        if (category && task) {
            return `濮旀墭${category}: ${task}`;
        }
        return task ? `濮旀墭浠诲姟: ${task}` : '濮旀墭浠诲姟';
    }

    if (tool === 'todos' || tool === 'todowrite') {
        const todoCount = input.todos ? input.todos.length : 0;
        return todoCount > 0 ? `鏇存柊浠诲姟鍒楄〃 (${todoCount}椤?` : '鏇存柊浠诲姟鍒楄〃';
    }

    if (tool === 'skill') {
        const skillName = input.name || input.skill;
        return skillName ? `鍔犺浇鎶€鑳? ${skillName}` : '鍔犺浇鎶€鑳?;
    }

    // === 缃戠粶宸ュ叿 ===
    if (tool === 'browser') {
        const action = input.action || input.url;
        return action ? `娴忚鍣ㄦ搷浣? ${action}` : '娴忚鍣ㄦ搷浣?;
    }

    if (tool === 'web_search' || tool === 'search') {
        const query = input.query || input.q;
        return query ? `鎼滅储: ${query}` : '鎼滅储';
    }

    // === 鍏朵粬宸ュ叿 ===
    if (tool === 'system') {
        return '绯荤粺鎿嶄綔';
    }

    if (tool === 'database') {
        const action = input.mode || input.action;
        return action ? `鏁版嵁搴撴搷浣? ${action}` : '鏁版嵁搴撴搷浣?;
    }

    // 榛樿杩斿洖宸ュ叿鍚嶇О
    return toolType;
}

// 鍒涘缓浜嬩欢椤癸紙鎵ц鍔ㄤ綔锛?function createEventItem(event, index) {
    const item = document.createElement('div');

    // 鍒ゆ柇浜嬩欢绫诲瀷
    const isThought = event.type === 'thought';
    const isTool = event.type === 'tool' || event.type === 'action';
    const isError = event.type === 'error';

    let iconHtml, title, content, detailsHtml = '';
    let statusClass = 'text-gray-400';
    let statusIcon = 'schedule';
    let isExpandable = false;

    if (isThought) {
        iconHtml = TOOL_ICONS['thought'];
        title = 'thought';
        // 鏄剧ず瀹屾暣鐨勬€濊€冨唴瀹癸紝鑰屼笉鏄痶oken鏁?        content = event.content || event.data?.text || (typeof event.data === 'string' ? event.data : '') || '鎬濊€冧腑...';
        // 鉁?v=38.4.11 淇锛歵hought鍐呭浣跨敤markdown娓叉煋
        // 鍘熷洜锛欸LM-4.7鐨剅easoning鍐呭鍖呭惈markdown鏍煎紡锛堝垪琛ㄣ€佺矖浣撶瓑锛?        isExpandable = true;
    } else if (isError) {
        iconHtml = '<span class="material-symbols-outlined text-[14px]">error</span>';
        title = '鎵ц閿欒';
        content = event.content || event.message || '鍙戠敓浜嗘湭鐭ラ敊璇?;
        statusIcon = 'error';
        statusClass = 'text-red-500';
    } else if (isTool) {
        const data = event.data || {};
        const toolName = data.tool_name || event.tool || 'file_editor';
        const toolType = data.tool || toolName;

        if (typeof getToolIcon === 'function') {
            iconHtml = getToolIcon(toolType).icon;
        } else {
            iconHtml = TOOL_ICONS['file_editor'];
        }

        // 浣跨敤杈呭姪鍑芥暟鐢熸垚鍙嬪ソ鐨勬憳瑕?        const rawInput = data.input || {};
        const output = data.output || '';

        title = data.title || getToolSummary(toolName, rawInput, output);

        // 鎻愬彇杈撳叆杈撳嚭璇︽儏
        const inputIsNotEmpty = Object.keys(rawInput).length > 0;
        const input = inputIsNotEmpty ? JSON.stringify(rawInput, null, 2) : '';

        content = input ? `Input: ${input.substring(0, 100)}${input.length > 100 ? '...' : ''}` : (output || `${toolName} 鎿嶄綔`);

        if (input || output) {
            isExpandable = true;
            // 鉁?v=38.4.11 浼樺寲锛氬噺灏廱ash/terminal瀛椾綋澶у皬锛岀壒鍒拡瀵逛腑鏂囧瓧绗?            detailsHtml = `
                <div class="mt-2 p-2 bg-gray-50 dark:bg-black/20 rounded border border-gray-100 dark:border-white/5 font-mono text-[9px] leading-tight overflow-auto max-h-60">
                    ${inputIsNotEmpty ? `<div class="text-blue-500 mb-0.5">Incoming Input:</div><pre class="whitespace-pre-wrap mb-1">${escapeHtml(input)}</pre>` : ''}
                    ${output ? `<div class="text-green-500 mb-0.5">Command Output:</div><pre class="whitespace-pre-wrap">${escapeHtml(output)}</pre>` : ''}
                </div>
            `;
        }
    }

    // 鍩虹鏍峰紡
    item.className = 'event-item bg-white dark:bg-zinc-900/30 rounded-lg p-2.5 transition-colors border border-gray-200 dark:border-gray-700';

    item.innerHTML = `
        <div class="flex items-start gap-2">
            <div class="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                ${iconHtml}
            </div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-bold text-gray-700 dark:text-gray-200">${title}</span>
                </div>
                <div class="event-content text-xs text-gray-500 dark:text-gray-400 ${isExpandable ? 'line-clamp-1' : ''}">${isThought ? safeRenderMarkdown(content || '') : escapeHtml(content || '')}</div>
                <div class="event-details text-xs text-gray-500 dark:text-gray-400 hidden">${detailsHtml || (isThought ? safeRenderMarkdown(content || '') : escapeHtml(content || ''))}</div>
            </div>
            ${isExpandable ? `
                <div class="flex-shrink-0 expand-icon-wrapper cursor-pointer p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                    <span class="material-symbols-outlined text-gray-400 expand-icon transition-transform duration-200 text-[16px]">expand_more</span>
                </div>
            ` : ''}
        </div>
    `;

    if (isExpandable) {
        const expandWrapper = item.querySelector('.expand-icon-wrapper');
        const expandIcon = item.querySelector('.expand-icon');
        const eventContent = item.querySelector('.event-content');
        const eventDetails = item.querySelector('.event-details');

        expandWrapper.onclick = (e) => {
            e.stopPropagation();
            const isHidden = eventDetails.classList.contains('hidden');
            if (isHidden) {
                eventDetails.classList.remove('hidden');
                eventContent.classList.add('hidden');
                expandIcon.style.transform = 'rotate(180deg)';
            } else {
                eventDetails.classList.add('hidden');
                eventContent.classList.remove('hidden');
                expandIcon.style.transform = 'rotate(0deg)';
            }
        };
    }

    // 娣诲姞宸ュ叿浜嬩欢鐐瑰嚮鍝嶅簲
    if (isTool && !isThought) {
        item.style.cursor = 'pointer';
        item.onclick = () => {
            // 璋冪敤鍙充晶闈㈡澘鏄剧ず瀹屾暣鍐呭
            if (typeof window.rightPanelManager === 'object' && window.rightPanelManager) {
                const data = event.data || {};
                const toolName = data.tool_name || event.tool || '';
                const output = data.output || '';

                // 鏍规嵁宸ュ叿绫诲瀷鍐冲畾鏄剧ず鏂瑰紡
                if (toolName.toLowerCase() === 'read' || toolName.toLowerCase().includes('read')) {
                    // read 宸ュ叿 - 鏄剧ず鏂囦欢鍐呭
                    const input = data.input || {};
                    const filePath = input.path || input.file_path || 'unknown';
                    window.rightPanelManager.showFileEditor(filePath, output);
                } else if (output && typeof output === 'string' && output.length > 0) {
                    // bash/grep 绛夊伐鍏?- 鏄剧ず杈撳嚭
                    window.rightPanelManager.showFileEditor(`${toolName} 杈撳嚭`, output);
                }
            }
        };
    }

    return item;
}

// 鍒涘缓鍗曚釜鍔ㄤ綔椤?function createActionItem(action, index) {
    const item = document.createElement('div');

    // 鍒ゆ柇鍔ㄤ綔绫诲瀷
    const isThought = action.type === 'thought';
    const isError = action.type === 'error';

    // 鏍规嵁绫诲瀷璁剧疆鍥炬爣鍜屾爣棰?    let iconName, title, content;
    let statusClass = 'text-gray-400';
    let statusIcon = 'schedule';

    if (isThought) {
        // 鎬濊€冪被鍨?        iconName = 'psychology';
        title = 'thought';
        content = action.content || '';
    } else if (isError) {
        // 閿欒绫诲瀷
        iconName = 'error';
        title = '鎵ц閿欒';
        content = action.content || '鍙戠敓浜嗘湭鐭ラ敊璇?;
        statusIcon = 'error';
        statusClass = 'text-red-500';
    } else {
        // 宸ュ叿绫诲瀷鍔ㄤ綔锛坮ead, write, execute, bash, grep, test 绛夛級
        const toolType = action.tool || action.type || 'default';

        // 浣跨敤 getToolIcon 鑾峰彇鍥炬爣閰嶇疆
        if (typeof getToolIcon === 'function') {
            const toolConfig = getToolIcon(toolType);
            iconName = toolConfig.icon;
        } else {
            iconName = 'extension';
        }

        title = toolType;
        content = action.description || action.brief || `${toolType} 鎿嶄綔`;
    }

    // 鑾峰彇宸ュ叿鍥炬爣閰嶇疆锛堜娇鐢ㄧ伆鑹茬郴锛?    const toolIconHtml = `
        <div class="flex items-center justify-center bg-gray-100 dark:bg-zinc-800 rounded-lg p-1.5 flex-shrink-0">
            <span class="material-symbols-outlined text-gray-600 dark:text-gray-400 text-[16px]">
                ${iconName}
            </span>
        </div>
    `;

    item.className = 'action-item bg-gray-50 dark:bg-zinc-800/50 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer border border-transparent hover:border-primary/20 mb-2';
    item.innerHTML = `
        <div class="flex items-start gap-3">
            ${toolIconHtml}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-bold text-gray-700 dark:text-gray-200">${title}</span>
                    <span class="text-[10px] text-gray-400 font-mono">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 font-mono bg-black/5 dark:bg-white/5 p-2 rounded-lg border border-border-light dark:border-border-dark break-all line-clamp-3">${escapeHtml(content || '')}</div>
            </div>
            <div class="flex-shrink-0">
                <span class="material-symbols-outlined ${statusClass} text-[14px]">${statusIcon}</span>
            </div>
        </div>
    `;

    // 鐐瑰嚮灞曞紑璇︽儏
    item.onclick = () => {
        if (window.showActionDetail) window.showActionDetail(action);
    };

    return item;
}

// 鍒涘缓浠诲姟浜や粯鍗＄墖
function createDeliverableCard(session) {
    const card = document.createElement('div');
    card.className = 'space-y-6';

    // 鏃╁嚭鍙ｏ細濡傛灉娌℃湁浜や粯鐗╋紝鍙樉绀哄搷搴斿唴瀹?    const hasDeliverables = session.deliverables && session.deliverables.length > 0;
    if (!hasDeliverables) {
        // 鉁?浠ｇ爜瀹℃煡淇 #1: 浣跨敤safeRenderMarkdown闃叉XSS锛岃€屼笉鏄痬arked.parse
        card.innerHTML = `
            <div class="space-y-4">
                ${session.response ? `
                    <div>
                        ${safeRenderMarkdown(session.response)}
                    </div>
                ` : '<p class="text-slate-600 dark:text-slate-400">浠诲姟姝ｅ湪鎵ц涓?..</p>'}
            </div>
        `;
        return card;
    }

    // 鉁?浠ｇ爜瀹℃煡淇 #2: 浣跨敤杈呭姪鍑芥暟娑堥櫎閲嶅浠ｇ爜
    // 鍒嗙被鏂囦欢锛氱綉椤垫枃浠?vs 闈炵綉椤垫枃浠?    const webExtensions = ['html', 'htm'];
    const allFiles = session.deliverables;

    const webFiles = allFiles.filter(f => {
        const { ext } = extractFileInfo(f);
        return webExtensions.includes(ext);
    });

    const docFiles = allFiles.filter(f => {
        const { ext } = extractFileInfo(f);
        return !webExtensions.includes(ext);
    });

    const hasWebFiles = webFiles.length > 0;
    const hasDocFiles = docFiles.length > 0;
    const showMoreDocFiles = docFiles.length > 4;
    const displayDocFiles = docFiles.slice(0, 4);

    // 鉁?浠ｇ爜瀹℃煡淇 #1: 鍝嶅簲鍐呭涔熶娇鐢╯afeRenderMarkdown闃叉XSS
    card.innerHTML = `
        <div class="space-y-4">
            ${session.response ? `
                <div>
                    ${safeRenderMarkdown(session.response)}
                </div>
            ` : '<p class="text-slate-600 dark:text-slate-400">浠诲姟姝ｅ湪鎵ц涓?..</p>'}
        </div>

        <div class="space-y-4">
            <h2 class="text-xl font-semibold text-slate-900 dark:text-white">
                浜や粯鏂囦欢
            </h2>

            ${hasWebFiles ? `
                <div class="space-y-3">
                    <div class="grid grid-cols-1 gap-3" id="web-file-cards-${session.id}">
                        ${webFiles.map((file, idx) => {
        // 鉁?浠ｇ爜瀹℃煡淇 #2: 浣跨敤杈呭姪鍑芥暟鎻愬彇鏂囦欢淇℃伅
        const { fileName, ext } = extractFileInfo(file);
        // 鉁?浠ｇ爜瀹℃煡淇 #1: 娣诲姞鏂囦欢璺緞楠岃瘉
        if (!isValidFilePath(fileName)) {
            console.warn('[Security] Skipping invalid file path:', fileName);
            return '';
        }
        const previewUrl = `/opencode/preview_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`;
        const iconAndColor = getFileIconAndColor(ext);

        return `
                                <div class="web-file-card flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800 hover:border-blue-300 dark:hover:border-blue-700 transition-all rounded-xl group cursor-pointer"
                                     data-file-name="${escapeHtml(fileName)}" data-preview-url="${previewUrl}">
                                    <div class="flex items-center gap-3 min-w-0">
                                        <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                            <span class="material-symbols-outlined ${iconAndColor.color} text-xl">${iconAndColor.icon}</span>
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="text-[14px] leading-snug text-slate-700 dark:text-slate-300 font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                                                ${escapeHtml(fileName)}
                                            </div>
                                            <div class="text-xs text-slate-500 dark:text-slate-400">
                                                HTML 鏂囦欢
                                            </div>
                                        </div>
                                    </div>
                                    <button class="preview-btn flex-shrink-0 p-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors opacity-0 group-hover:opacity-100 flex items-center gap-2">
                                        <span class="material-symbols-outlined text-[18px]">visibility</span>
                                        <span class="text-sm font-medium">棰勮</span>
                                    </button>
                                </div>
                            `;
    }).join('')}
                    </div>
                </div>
            ` : ''}
            
            ${hasDocFiles ? `
                <div class="space-y-3">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3" id="doc-file-cards-${session.id}">
                        ${displayDocFiles.map((file, idx) => {
        // 鉁?浠ｇ爜瀹℃煡淇 #2: 浣跨敤杈呭姪鍑芥暟鎻愬彇鏂囦欢淇℃伅
        const { fileName, ext } = extractFileInfo(file);
        // 鉁?浠ｇ爜瀹℃煡淇 #1: 娣诲姞鏂囦欢璺緞楠岃瘉
        if (!isValidFilePath(fileName)) {
            console.warn('[Security] Skipping invalid file path:', fileName);
            return '';
        }
        const iconAndColor = getFileIconAndColor(ext);

        return `
                                <div class="file-card flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all rounded-xl group relative"
                                     data-file-name="${escapeHtml(fileName)}" data-file-ext="${ext}">
                                    <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                        <span class="material-symbols-outlined ${iconAndColor.color} text-xl">${iconAndColor.icon}</span>
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <div class="text-[13px] leading-snug text-slate-700 dark:text-slate-300 font-medium overflow-hidden text-ellipsis whitespace-nowrap">
                                            ${escapeHtml(fileName)}
                                        </div>
                                    </div>
                                    <!-- 鎿嶄綔鎸夐挳鑿滃崟 -->
                                    <div class="file-actions relative">
                                        <button class="action-menu-btn p-1 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded transition-colors opacity-0 group-hover:opacity-100">
                                            <span class="material-symbols-outlined text-gray-500 dark:text-gray-400 text-[18px]">more_horiz</span>
                                        </button>
                                        <div class="action-menu hidden absolute right-0 top-8 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-lg shadow-lg py-1 z-50 min-w-[140px]">
                                            ${ext === 'html' ? `
                                                <button class="view-source-btn w-full px-3 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-zinc-700 flex items-center gap-2">
                                                    <span class="material-symbols-outlined text-[16px]">code</span>
                                                    鏌ョ湅婧愮爜
                                                </button>
                                            ` : ''}
                                            <button class="delete-file-btn w-full px-3 py-2 text-left text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2">
                                                <span class="material-symbols-outlined text-[16px]">delete</span>
                                                鍒犻櫎
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            `;
    }).join('')}
                        ${showMoreDocFiles ? `
                            <div class="view-all-files flex items-center gap-3 p-3 bg-card-light dark:bg-card-dark border border-transparent hover:border-slate-200 dark:hover:border-slate-700 transition-all cursor-pointer rounded-xl group md:col-span-2 md:max-w-sm">
                                <div class="w-10 h-10 flex-shrink-0 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm">
                                    <span class="material-symbols-outlined text-blue-500 text-xl">folder_open</span>
                                </div>
                                <div class="text-[13px] leading-snug text-slate-700 dark:text-slate-300 font-medium">
                                    鏌ョ湅鎵€鏈夋枃浠?                                </div>
                                <div class="text-xs text-slate-400 dark:text-slate-500 ml-auto">
                                    ${docFiles.length} 涓枃浠?                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            ` : ''}
        </div>
    `;

    // 缁戝畾缃戦〉鏂囦欢鍗＄墖鐐瑰嚮浜嬩欢
    if (hasWebFiles) {
        const webFileCards = card.querySelectorAll('.web-file-card');
        webFileCards.forEach(fileCard => {
            const previewUrl = fileCard.getAttribute('data-preview-url');
            const fileName = fileCard.getAttribute('data-file-name');

            // 鐐瑰嚮棰勮鎸夐挳
            const previewBtn = fileCard.querySelector('.preview-btn');
            if (previewBtn) {
                previewBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    console.log('[Deliverable] Preview web file:', fileName);
                    if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                        window.rightPanelManager.showWebPreview(session.id, fileName);
                    }
                });
            }

            // 鐐瑰嚮鏁翠釜鍗＄墖涔熻Е鍙戦瑙?            fileCard.addEventListener('click', (e) => {
                if (e.target.closest('.preview-btn')) return;
                console.log('[Deliverable] Click web file card:', fileName);
                if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                    window.rightPanelManager.showWebPreview(session.id, fileName);
                }
            });
        });
    }

    // 缁戝畾鏂囨。鏂囦欢鍗＄墖鐐瑰嚮浜嬩欢
    if (hasDocFiles) {
        const fileCards = card.querySelectorAll('.file-card');
        fileCards.forEach(fileCard => {
            const fileName = fileCard.getAttribute('data-file-name');
            const fileExt = fileCard.getAttribute('data-file-ext');

            // 鐐瑰嚮鍗＄墖涓讳綋锛堜笉鍖呮嫭鎿嶄綔鎸夐挳锛?            fileCard.addEventListener('click', (e) => {
                // 濡傛灉鐐瑰嚮鐨勬槸鎿嶄綔鎸夐挳鎴栬彍鍗曪紝涓嶈Е鍙戝崱鐗囩偣鍑?                if (e.target.closest('.file-actions')) return;

                console.log('鐐瑰嚮鏂囦欢鍗＄墖:', fileName, '鎵╁睍鍚?', fileExt);

                // HTML鏂囦欢榛樿棰勮缃戦〉
                if (fileExt === 'html') {
                    console.log('[FileCard] Loading HTML preview:', fileName);

                    if (window.rightPanelManager && typeof window.rightPanelManager.showWebPreview === 'function') {
                        window.rightPanelManager.showWebPreview(session.id, fileName);
                    }
                } else {
                    // 鍏朵粬鏂囦欢鏄剧ず婧愮爜
                    if (window.rightPanelManager && typeof window.rightPanelManager.showFileEditor === 'function') {
                        window.rightPanelManager.showFileEditor(fileName, '鍔犺浇涓?..');
                        // 瀹為檯鍔犺浇鏂囦欢鍐呭
                        fetch(`/opencode/read_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`)
                            .then(res => {
                                // 鉁?浠ｇ爜瀹℃煡淇 #2: 鏀硅繘閿欒澶勭悊 - 鎻愪緵鏇磋缁嗙殑HTTP閿欒淇℃伅
                                if (!res.ok) {
                                    // 鏍规嵁HTTP鐘舵€佺爜鎻愪緵鏇村叿浣撶殑閿欒淇℃伅
                                    if (res.status === 404) {
                                        throw new Error('鏂囦欢涓嶅瓨鍦ㄦ垨宸茶鍒犻櫎');
                                    } else if (res.status === 403) {
                                        throw new Error('娌℃湁璁块棶鏉冮檺');
                                    } else if (res.status >= 500) {
                                        throw new Error('鏈嶅姟鍣ㄩ敊璇紝璇风◢鍚庨噸璇?);
                                    } else {
                                        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                                    }
                                }
                                return res.json();
                            })
                            .then(data => {
                                if (data.status === 'success' && data.content) {
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, data.content);
                                    }
                                } else {
                                    console.error('璇诲彇鏂囦欢澶辫触:', data);
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, `鏃犳硶璇诲彇鏂囦欢: ${data.message || '鏈煡閿欒'}`);
                                    }
                                }
                            })
                            .catch(err => {
                                console.error('璇诲彇鏂囦欢鍑洪敊:', err);
                                if (window.rightPanelManager) {
                                    window.rightPanelManager.showFileEditor(fileName, `鏃犳硶璇诲彇鏂囦欢: ${err.message}`);
                                }
                            });
                    }
                }
            });

            // 鎿嶄綔鑿滃崟鎸夐挳鐐瑰嚮
            const menuBtn = fileCard.querySelector('.action-menu-btn');
            const menu = fileCard.querySelector('.action-menu');
            if (menuBtn && menu) {
                menuBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // 鍏抽棴鍏朵粬鎵撳紑鐨勮彍鍗?                    card.querySelectorAll('.action-menu').forEach(m => {
                        if (m !== menu) m.classList.add('hidden');
                    });
                    menu.classList.toggle('hidden');
                });

                // 鏌ョ湅婧愮爜鎸夐挳锛堜粎HTML鏂囦欢锛?                const viewSourceBtn = fileCard.querySelector('.view-source-btn');
                if (viewSourceBtn) {
                    viewSourceBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        menu.classList.add('hidden');
                        console.log('鏌ョ湅婧愮爜:', fileName);
                        // 璇诲彇鏂囦欢鍐呭骞舵樉绀?                        fetch(`/opencode/read_file?session_id=${session.id}&file_path=${encodeURIComponent(fileName)}`)
                            .then(res => {
                                // 鉁?浠ｇ爜瀹℃煡淇 #2: 鏀硅繘閿欒澶勭悊 - 鎻愪緵鏇磋缁嗙殑HTTP閿欒淇℃伅
                                if (!res.ok) {
                                    if (res.status === 404) {
                                        throw new Error('鏂囦欢涓嶅瓨鍦ㄦ垨宸茶鍒犻櫎');
                                    } else if (res.status === 403) {
                                        throw new Error('娌℃湁璁块棶鏉冮檺');
                                    } else if (res.status >= 500) {
                                        throw new Error('鏈嶅姟鍣ㄩ敊璇紝璇风◢鍚庨噸璇?);
                                    } else {
                                        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
                                    }
                                }
                                return res.json();
                            })
                            .then(data => {
                                if (data.status === 'success' && data.content) {
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, data.content);
                                    }
                                } else {
                                    console.error('璇诲彇鏂囦欢澶辫触:', data);
                                    if (window.rightPanelManager) {
                                        window.rightPanelManager.showFileEditor(fileName, `鏃犳硶璇诲彇鏂囦欢: ${data.message || '鏈煡閿欒'}`);
                                    }
                                }
                            })
                            .catch(err => {
                                console.error('璇诲彇鏂囦欢鍑洪敊:', err);
                                if (window.rightPanelManager) {
                                    window.rightPanelManager.showFileEditor(fileName, `鏃犳硶璇诲彇鏂囦欢: ${err.message}`);
                                }
                            });
                    });
                }

                // 鍒犻櫎鎸夐挳
                const deleteBtn = fileCard.querySelector('.delete-file-btn');
                if (deleteBtn) {
                    deleteBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        menu.classList.add('hidden');
                        if (confirm(`纭畾瑕佸垹闄ゆ枃浠?"${fileName}" 鍚楋紵`)) {
                            console.log('鍒犻櫎鏂囦欢:', fileName);
                            // 浠巇eliverables涓Щ闄?                            const index = session.deliverables.findIndex(f => {
                                const fName = typeof f === 'string' ? f : (f.name || f.path);
                                return fName === fileName;
                            });
                            if (index > -1) {
                                session.deliverables.splice(index, 1);
                                // 閲嶆柊娓叉煋
                                if (typeof window.renderResults === 'function') {
                                    window.renderResults();
                                }
                            }
                        }
                    });
                }
            }
        });

        // 鐐瑰嚮鍏朵粬鍦版柟鍏抽棴鎵€鏈夎彍鍗?        card.addEventListener('click', (e) => {
            if (!e.target.closest('.file-actions')) {
                card.querySelectorAll('.action-menu').forEach(m => m.classList.add('hidden'));
            }
        });

        // 缁戝畾"鏌ョ湅鎵€鏈夋枃浠?鎸夐挳
        const viewAllBtn = card.querySelector('.view-all-files');
        if (viewAllBtn) {
            viewAllBtn.onclick = () => {
                // 鍒囨崲鍒板彸渚ч潰鏉跨殑Files鏍囩
                if (window.rightPanelManager && typeof window.rightPanelManager.switchTab === 'function') {
                    window.rightPanelManager.switchTab('files');
                } else if (typeof togglePanel === 'function') {
                    togglePanel('files');
                } else {
                    console.warn('鏃犳硶鎵撳紑鏂囦欢闈㈡澘');
                }
            };
        }
    }

    return card;
}

// 鏍规嵁鏂囦欢鎵╁睍鍚嶈幏鍙栧浘鏍囧拰棰滆壊
function getFileIconAndColor(ext) {
    const iconMap = {
        // 鍥剧墖
        'png': { icon: 'image', color: 'text-purple-500' },
        'jpg': { icon: 'image', color: 'text-purple-500' },
        'jpeg': { icon: 'image', color: 'text-purple-500' },
        'gif': { icon: 'image', color: 'text-purple-500' },
        'svg': { icon: 'image', color: 'text-purple-500' },
        'webp': { icon: 'image', color: 'text-purple-500' },

        // 鏂囨。
        'pdf': { icon: 'picture_as_pdf', color: 'text-red-500' },
        'doc': { icon: 'description', color: 'text-blue-500' },
        'docx': { icon: 'description', color: 'text-blue-500' },
        'xls': { icon: 'table_chart', color: 'text-green-500' },
        'xlsx': { icon: 'table_chart', color: 'text-green-500' },
        'ppt': { icon: 'slideshow', color: 'text-orange-500' },
        'pptx': { icon: 'slideshow', color: 'text-orange-500' },
        'txt': { icon: 'text_snippet', color: 'text-gray-500' },
        'md': { icon: 'markdown', color: 'text-gray-600' },

        // 浠ｇ爜
        'js': { icon: 'javascript', color: 'text-yellow-500' },
        'ts': { icon: 'data_object', color: 'text-blue-600' },
        'py': { icon: 'code', color: 'text-blue-400' },
        'java': { icon: 'code', color: 'text-red-500' },
        'cpp': { icon: 'code', color: 'text-blue-500' },
        'c': { icon: 'code', color: 'text-blue-500' },
        'html': { icon: 'html', color: 'text-orange-500' },
        'css': { icon: 'css', color: 'text-blue-500' },
        'json': { icon: 'data_object', color: 'text-yellow-600' },

        // 鍏朵粬
        'zip': { icon: 'folder_zip', color: 'text-amber-500' },
        'rar': { icon: 'folder_zip', color: 'text-amber-500' },
    };

    return iconMap[ext] || { icon: 'insert_drive_file', color: 'text-gray-500' };
}

// 鏄剧ず浜嬩欢璇︽儏寮圭獥
function showEventDetail(event) {
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4 animate-fade-in';

    const isThought = event.type === 'thought';
    const isTool = event.type === 'tool';
    const isError = event.type === 'error';

    let eventTitle = '浜嬩欢璇︽儏';
    if (isThought) eventTitle = '鎬濊€冭繃绋?;
    else if (isTool) eventTitle = `宸ュ叿鎿嶄綔: ${event.tool || 'unknown'}`;
    else if (isError) eventTitle = '鎵ц閿欒';

    modal.innerHTML = `
        <div class="bg-white dark:bg-surface-dark rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div class="px-6 py-4 border-b border-border-light dark:border-border-dark flex items-center justify-between">
                <h3 class="text-lg font-bold text-gray-900 dark:text-white">${eventTitle}</h3>
                <button class="close-modal p-1 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded transition-colors">
                    <span class="material-symbols-outlined text-gray-500">close</span>
                </button>
            </div>
            <div class="flex-1 overflow-y-auto p-6 space-y-4">
                ${event.type ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">绫诲瀷</div>
                        <div class="text-sm px-3 py-2 bg-gray-100 dark:bg-zinc-800 rounded">${escapeHtml(event.type)}</div>
                    </div>
                ` : ''}
                ${event.tool ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">宸ュ叿</div>
                        <div class="text-sm px-3 py-2 bg-gray-100 dark:bg-zinc-800 rounded font-mono">${escapeHtml(event.tool)}</div>
                    </div>
                ` : ''}
                ${event.content ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">鍐呭</div>
                        <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">${escapeHtml(event.content)}</div>
                    </div>
                ` : ''}
                ${event.args ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">鍙傛暟</div>
                        <pre class="text-xs font-mono p-3 bg-gray-100 dark:bg-zinc-800 rounded overflow-x-auto">${JSON.stringify(event.args, null, 2)}</pre>
                    </div>
                ` : ''}
                ${event.result ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">缁撴灉</div>
                        <pre class="text-xs font-mono p-3 bg-gray-100 dark:bg-zinc-800 rounded overflow-x-auto max-h-[300px]">${JSON.stringify(event.result, null, 2)}</pre>
                    </div>
                ` : ''}
                ${event.timestamp ? `
                    <div>
                        <div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">鏃堕棿鎴?/div>
                        <div class="text-sm text-gray-700 dark:text-gray-300">${escapeHtml(event.timestamp)}</div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;

    modal.onclick = (e) => {
        if (e.target === modal || e.target.closest('.close-modal')) {
            modal.remove();
        }
    };

    document.body.appendChild(modal);
}

// HTML 杞箟宸ュ叿鍑芥暟
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 鉁?浠ｇ爜瀹℃煡淇 #3: 浼樺寲鍏ㄥ眬鑿滃崟鐩戝惉鍣ㄦ€ц兘 - 鍙湪鑿滃崟鏄剧ず鏃舵墠鏌ヨDOM
// 淇闂锛欼mportant #3 - 姣忔鐐瑰嚮閮絨uerySelectorAll褰卞搷鎬ц兘
document.addEventListener('click', (e) => {
    // 鍙湪鑿滃崟鏄剧ず鏃舵墠鏌ヨ锛堟€ц兘浼樺寲锛?    const visibleMenus = document.querySelectorAll('.action-menu:not(.hidden)');
    if (visibleMenus.length > 0 && !e.target.closest('.file-actions')) {
        visibleMenus.forEach(m => m.classList.add('hidden'));
    }
});

// 瀵煎嚭鍑芥暟
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { renderEnhancedTaskPanel };
}

// 鎸傝浇鍒板叏灞€浣滅敤鍩燂紝纭繚鍏朵粬鑴氭湰鍙互璁块棶锛堟祻瑙堝櫒鐜锛?window.renderEnhancedTaskPanel = renderEnhancedTaskPanel;


