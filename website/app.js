(() => {
const $=id=>document.getElementById(id);
const demo={symbol:"XAU / USD",timeframe:"15m",direction:"neutral",confidence:0,kfoo:"0/5",flow:"—",execution:"OFF",gravity4:"—",gravity1:"—",entry5:"—",entry3:"—",table:"—",rsi:"—",whale:"—",buy:"—",sell:"—",level:"WAIT",score:0};
function paint(s){
 $("symbol").textContent=s.symbol||"—"; $("timeframe").textContent=s.timeframe||"—";
 const d=s.direction||"neutral"; $("direction").textContent=d==="long"?"شراء":d==="short"?"بيع":"محايد"; $("direction").className=d==="long"?"green":d==="short"?"red":"";
 $("confidence").textContent=Math.round((Number(s.confidence)||0)*100)+"%";
 $("kfoo").textContent=s.kfoo||"0/5"; $("flow").textContent=s.flow||"—";
 $("g4").textContent=s.gravity4||s.gravity?.["4h"]||"—"; $("g1").textContent=s.gravity1||s.gravity?.["1h"]||"—"; $("e5").textContent=s.entry5||s.timing?.["5m"]||"—"; $("e3").textContent=s.entry3||s.timing?.["3m"]||"—";
 $("table").textContent=s.table||"—"; $("rsi").textContent=s.rsi||"—"; $("whale").textContent=s.whale||"—"; $("buy").textContent=s.buy||"—"; $("sell").textContent=s.sell||"—";
 const g4=s.gravity4||s.gravity?.["4h"]; const g1=s.gravity1||s.gravity?.["1h"]; $("gravityBar").style.width=(g4&&g4===g1&&g4!=="—")?"100%":"0%";
 const level=s.level||"WAIT"; $("kfooText").textContent=level==="STRONG_ENTRY"?"إشارة دخول قوية":level==="STRONG_SETUP"?"إعداد قوي — بانتظار التوقيت":"لا توجد إشارة قوية";
 $("gate").textContent=level==="STRONG_ENTRY"?"5M + 3M متوافقان — إشارة قوية":level==="STRONG_SETUP"?"الإعداد مؤكد — بانتظار التوقيت":"بانتظار توافق الشروط";
 $("updated").textContent=s.updated_at?new Date(Number(s.updated_at)*1000).toLocaleTimeString("ar-SA"):"بانتظار الوكيل";
 $("status").textContent="ONLINE";
}
async function refresh(){try{const r=await fetch("/api/public-state",{cache:"no-store"});if(!r.ok)throw new Error();paint(await r.json())}catch(e){$("status").textContent="OFFLINE";$("updated").textContent="بانتظار الاتصال"}}
paint(demo); refresh(); setInterval(refresh,1500);
})();