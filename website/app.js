(() => {
const $=id=>document.getElementById(id);
const demo={symbol:"BTC / USDT",timeframe:"15m",direction:"neutral",confidence:0,kfoo:"0/5",flow:"—",execution:"OFF",gravity4:"—",gravity1:"—",entry5:"—",entry3:"—",table:"—",rsi:"—",whale:"—",buy:"—",sell:"—"};
function paint(s){
$("symbol").textContent=s.symbol||"—";$("timeframe").textContent=s.timeframe||"—";
$("direction").textContent=s.direction==="long"?"شراء":s.direction==="short"?"بيع":"محايد";
$("direction").className=s.direction==="long"?"green":s.direction==="short"?"red":"";
$("confidence").textContent=Math.round((Number(s.confidence)||0)*100)+"%";
$("kfoo").textContent=s.kfoo||"0/5";$("flow").textContent=s.flow||"—";
$("g4").textContent=s.gravity4||"—";$("g1").textContent=s.gravity1||"—";$("e5").textContent=s.entry5||"—";$("e3").textContent=s.entry3||"—";
$("table").textContent=s.table||"—";$("rsi").textContent=s.rsi||"—";$("whale").textContent=s.whale||"—";$("buy").textContent=s.buy||"—";$("sell").textContent=s.sell||"—";
$("gravityBar").style.width=(s.gravity4&&s.gravity4===s.gravity1&&s.gravity4!=="—")?"100%":"0%";
$("kfooText").textContent=s.kfoo==="5/5"?"توافق كامل للمكونات":"لا توجد إشارة مؤكدة";
$("gate").textContent=s.ready?"الشروط متوافقة — جاهز للمراجعة":"بانتظار توافق الشروط";
}
paint(demo);
})();