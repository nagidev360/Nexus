/* Nexus Support Chat — lightweight FAQ widget, no account or API key required. */
(() => {
  if (document.getElementById("nexusSupportLauncher")) return;
  const style = document.createElement("style");
  style.textContent = `
  #nexusSupportLauncher{position:fixed;right:22px;bottom:22px;z-index:9998;border:0;border-radius:999px;padding:14px 18px;background:#7667ff;color:#fff;font:600 14px inherit;box-shadow:0 10px 35px #0005;cursor:pointer}
  #nexusSupportPanel{position:fixed;right:22px;bottom:84px;z-index:9999;width:min(360px,calc(100vw - 28px));height:min(500px,calc(100dvh - 120px));display:none;flex-direction:column;overflow:hidden;border:1px solid #ffffff20;border-radius:18px;background:#101625;color:#f5f7ff;box-shadow:0 18px 60px #0008;font:14px/1.45 system-ui,-apple-system,sans-serif}
  #nexusSupportPanel.open{display:flex}#nexusSupportPanel *{box-sizing:border-box}
  .nsc-head{display:flex;align-items:center;justify-content:space-between;padding:16px;background:linear-gradient(120deg,#272752,#151d31);border-bottom:1px solid #ffffff18}
  .nsc-head strong{display:block;font-size:16px}.nsc-head small{color:#b9c2dc}.nsc-close{border:0;background:transparent;color:#fff;font-size:24px;cursor:pointer}
  .nsc-messages{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px}
  .nsc-msg{max-width:92%;padding:10px 12px;border-radius:13px;background:#202a3e;color:#f5f7ff;white-space:pre-wrap}.nsc-msg.bot{align-self:flex-start;border-bottom-left-radius:4px}.nsc-msg.user{align-self:flex-end;background:#635bdb;border-bottom-right-radius:4px}
  .nsc-choices{padding:0 12px 12px;display:flex;flex-wrap:wrap;gap:7px}.nsc-choice{border:1px solid #7770e8;background:#171d30;color:#e9e8ff;border-radius:999px;padding:8px 10px;cursor:pointer;font-size:12px}
  .nsc-form{display:flex;gap:8px;padding:12px;border-top:1px solid #ffffff18}.nsc-form input{min-width:0;flex:1;border:1px solid #39445b;border-radius:10px;background:#0b1120;color:#fff;padding:11px}.nsc-form button{border:0;border-radius:10px;background:#7667ff;color:#fff;padding:0 13px;cursor:pointer}
  .nsc-foot{padding:0 12px 10px;color:#929db7;font-size:11px}.nsc-foot a{color:#c4bdff}
  @media(max-width:480px){#nexusSupportLauncher{right:14px;bottom:14px}#nexusSupportPanel{right:10px;bottom:72px;width:calc(100vw - 20px);height:min(520px,calc(100dvh - 95px))}}
  `;
  document.head.appendChild(style);
  const launcher = document.createElement("button");
  launcher.id = "nexusSupportLauncher"; launcher.type = "button";
  launcher.setAttribute("aria-controls","nexusSupportPanel"); launcher.setAttribute("aria-expanded","false");
  launcher.textContent = "💬 Help";
  const panel = document.createElement("section");
  panel.id = "nexusSupportPanel"; panel.setAttribute("role","dialog"); panel.setAttribute("aria-label","Nexus Support");
  panel.innerHTML = '<div class="nsc-head"><div><strong>Nexus Support</strong><small>Quick help with the website</small></div><button class="nsc-close" type="button" aria-label="Close support chat">×</button></div><div class="nsc-messages" aria-live="polite"></div><div class="nsc-choices"></div><form class="nsc-form"><input aria-label="Ask a question" maxlength="300" placeholder="Type your question…" autocomplete="off"><button type="submit">Send</button></form><div class="nsc-foot">Automated FAQ support · <a href="https://discord.gg/v9HNmb3VFM" target="_blank" rel="noopener noreferrer">Contact support on Discord ↗</a></div>';
  document.body.append(launcher,panel);
  const messages = panel.querySelector(".nsc-messages"), choices = panel.querySelector(".nsc-choices"), input = panel.querySelector("input");
  const faqs = [
    ["How do I download an app?","Open a listing, review its details, then select Download. Only install files from publishers you trust."],
    ["The download is not working","Refresh the page and try again. If the listing still fails, contact Nexus support on Discord and include the app name."],
    ["Is Nexus an official app store?","Nexus is a software discovery website. Check the publisher and scan downloaded files before installing."],
    ["How do I report a problem?","Contact Nexus support on Discord using the link below. Share the page URL and a short description—never send passwords."],
    ["How do I upload software?","If you are an authorized publisher, contact the Nexus site administrator for upload access."]
  ];
  function addMessage(text,who){const el=document.createElement("div");el.className="nsc-msg "+who;el.textContent=text;messages.appendChild(el);messages.scrollTop=messages.scrollHeight;}
  function answer(question){
    const q=question.toLowerCase();
    const found=faqs.find(([title])=>title.toLowerCase().split(/[^a-z]+/).filter(w=>w.length>3).some(w=>q.includes(w)));
    if(/download|install|apk/.test(q)) return faqs[0][1];
    if(/error|fail|broken|problem|not work/.test(q)) return faqs[1][1];
    if(/official|safe|virus|trust/.test(q)) return faqs[2][1];
    if(/report|contact|support|help|discord/.test(q)) return faqs[3][1];
    if(/upload|publish|add app/.test(q)) return faqs[4][1];
    if(found) return found[1];
    return "I can help with downloads, download errors, safety, reporting issues, and publisher access. Choose a topic below or contact our support team on Discord.";
  }
  function ask(q){q=q.trim();if(!q)return;addMessage(q,"user");addMessage(answer(q),"bot");}
  function showChoices(){choices.replaceChildren();faqs.forEach(([title])=>{const b=document.createElement("button");b.type="button";b.className="nsc-choice";b.textContent=title;b.addEventListener("click",()=>ask(title));choices.appendChild(b);});}
  launcher.addEventListener("click",()=>{const open=!panel.classList.contains("open");panel.classList.toggle("open",open);launcher.setAttribute("aria-expanded",String(open));if(open)input.focus();});
  panel.querySelector(".nsc-close").addEventListener("click",()=>{panel.classList.remove("open");launcher.setAttribute("aria-expanded","false");launcher.focus();});
  panel.querySelector("form").addEventListener("submit",e=>{e.preventDefault();ask(input.value);input.value="";});
  addMessage("Hi! I’m the Nexus automated support assistant. What can I help you with?","bot");showChoices();
})();