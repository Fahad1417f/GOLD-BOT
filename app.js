(() => {
const RAW="https://raw.githubusercontent.com/Fahad1417f/GOLD-BOT/main/website_state.json";
const $=id=>document.getElementById(id);
const text=(id,v)=>{const e=$(id);if(e)e.textContent=v??"—"};
const val=(x)=>x===undefined||x===null||x===""?"—":String(x);
function dir(v){return v==="long"?"شراء":v==="short"?"بيع":"محايد"}
function pct(v){if(v===null||v===undefined||v==="")return"—";const n=Number(v);return isNaN(n)?"—":(n<=1?Math.round(n*100):Math.round(n))+"%"}
function paint(s){
 const stale=Date.now()-(Number(s.updated_at||0)*1000)>15*60*1000;
 text("symbol",val(s.symbol||"XAUUSD")); text("timeframe",val(s.timeframe||"15m"));
 const d=s.direction||"neutral"; text("direction",dir(d)); $("direction").className=d==="long"?"green":d==="short"?"red":"";
 text("confidence",pct(s.confidence)); text("g4",val(s.gravity?.["4h"])); text("g1",val(s.gravity?.["1h"]));
 const agree=s.gravity?.["4h"]&&s.gravity["4h"]===s.gravity?.["1h"]&&s.gravity["4h"]!=="unknown";
 $("gravityBar").style.width=agree?"100%":"0%";
 text("e5",val(s.timing?.["5m"])); text("e3",val(s.timing?.["3m"]));
 const k=s.kfoo||{}; text("table",k.table||s.kfoo_table||"—"); text("tfAgg",k.tf_agg||s.kfoo_tf_agg||"—"); text("indAgg",k.ind_agg||s.kfoo_ind_agg||"—");
 text("activeKfoo",k.active||s.kfoo_active||"—"); text("signalScore",val(s.score));
 const inds=k.indicators||{}; text("rsi",inds.RSI||"—"); text("macd",inds.MACD||"—");
 text("reasons",(s.reasons||[]).slice(0,2).join(" · ")||"قراءة KFOO منشورة");
 const level=s.level||"WAIT";
 text("kfoo",level==="STRONG_ENTRY"?"STRONG":level==="STRONG_SETUP"?"SETUP":val(k.score||"—"));
 text("kfooText",level==="STRONG_ENTRY"?"إشارة دخول قوية":level==="STRONG_SETUP"?"إعداد قوي — بانتظار التوقيت":"قراءة المراقب الحالية");
 text("gate",level==="STRONG_ENTRY"?"توافق الدخول مؤكد — التنفيذ ما زال متوقفًا":level==="STRONG_SETUP"?"الإعداد مؤكد — بانتظار فريمات الدخول":"بانتظار توافق الشروط");
 const online=!stale&&s.agent_status==="ONLINE";
 text("status",online?"ONLINE":"STALE"); text("connection",online?"CONNECTED":"STALE");
 text("agentState",online?"المراقب متصل":"المراقب غير متصل"); text("agentMode","التنفيذ متوقف · قراءة فقط");
 text("tv",online?"PASS":"WAIT"); text("vision",online?"PASS":"WAIT"); text("kfooState",online?"PASS":"WAIT");
 text("updated",s.updated_at?new Date(Number(s.updated_at)*1000).toLocaleTimeString("ar-SA"):"بانتظار الوكيل");
}
async function refresh(){
 try{
  const r=await fetch(RAW+"?v="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw new Error("state_http_"+r.status);
  paint(await r.json());
 }catch(e){
  text("status","OFFLINE");text("connection","OFFLINE");text("agentState","بانتظار الوكيل");text("updated","لا توجد بيانات");
 }
}
refresh();setInterval(refresh,5000);
})();