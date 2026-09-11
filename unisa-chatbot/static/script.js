/* UNISA Study Assistant - vanilla JS chat client. */
(function () {
  "use strict";

  var messagesEl = document.getElementById("messages");
  var typingEl = document.getElementById("typing");
  var formEl = document.getElementById("composer");
  var inputEl = document.getElementById("input");
  var sendBtn = document.getElementById("send-btn");
  var menuBtn = document.getElementById("menu-btn");
  var restartBtn = document.getElementById("restart-btn");

  var sessionId = null;
  var busy = false;
  var TYPING_DELAY = 500;

  /* Scroll the transcript to the newest message. */
  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  /* Disable earlier quick replies so only the latest set is clickable. */
  function lockOldChips() {
    var chips = messagesEl.querySelectorAll("button.chip");
    for (var i = 0; i < chips.length; i++) {
      chips[i].disabled = true;
    }
  }

  /* Append a message row. role is "user" or "bot". */
  function addMessage(role, text) {
    var row = document.createElement("div");
    row.className = "row " + role;

    var bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text; // textContent keeps \n via white-space: pre-wrap
    row.appendChild(bubble);

    messagesEl.appendChild(row);
    scrollToBottom();
    return row;
  }

  /* Render quick reply buttons and link buttons under a bot message. */
  function addActions(row, quickReplies, links) {
    var hasQuick = quickReplies && quickReplies.length;
    var hasLinks = links && links.length;
    if (!hasQuick && !hasLinks) {
      return;
    }

    var box = document.createElement("div");
    box.className = "actions";

    if (hasQuick) {
      quickReplies.forEach(function (item) {
        if (!item || !item.label) {
          return;
        }
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chip";
        btn.textContent = item.label;
        btn.addEventListener("click", function () {
          if (busy) {
            return;
          }
          send(item.value || item.label, item.label);
        });
        box.appendChild(btn);
      });
    }

    if (hasLinks) {
      links.forEach(function (item) {
        if (!item || !item.url) {
          return;
        }
        var anchor = document.createElement("a");
        anchor.className = "chip link";
        anchor.href = item.url;
        anchor.target = "_blank";
        anchor.rel = "noopener noreferrer";
        anchor.textContent = item.label || item.url;
        box.appendChild(anchor);
      });
    }

    row.appendChild(box);
    scrollToBottom();
  }

  /* Show a bot response after a short typing indicator. */
  function showBotResponse(data) {
    typingEl.hidden = false;
    scrollToBottom();
    window.setTimeout(function () {
      typingEl.hidden = true;
      var row = addMessage("bot", data.message || "Sorry, something went wrong.");
      addActions(row, data.quick_replies, data.links);
      busy = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }, TYPING_DELAY);
  }

  /* Send a message to the server. displayText is what the user sees echoed. */
  function send(value, displayText) {
    var text = (value === undefined || value === null) ? "" : String(value);
    if (busy) {
      return;
    }
    if (!text.trim()) {
      return;
    }

    busy = true;
    sendBtn.disabled = true;
    lockOldChips();
    addMessage("user", displayText || text);
    inputEl.value = "";

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId })
    })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (data && data.session_id) {
          sessionId = data.session_id;
        }
        showBotResponse(data || {});
      })
      .catch(function () {
        showBotResponse({
          message:
            "I couldn't reach the server. Check your connection and try again, " +
            "or call UNISA on 0800 00 1870.",
          quick_replies: [{ label: "Try again", value: "menu" }],
          links: []
        });
      });
  }

  formEl.addEventListener("submit", function (event) {
    event.preventDefault();
    send(inputEl.value);
  });

  menuBtn.addEventListener("click", function () {
    send("menu");
  });

  restartBtn.addEventListener("click", function () {
    messagesEl.innerHTML = "";
    sessionId = null;
    busy = false;
    sendBtn.disabled = false;
    send("hi");
  });

  /* Open with a greeting. */
  send("hi");
})();
