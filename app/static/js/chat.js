// 聊天室前端逻辑
let socket = null;
let currentUser = null;
let enterSend = false;
let lastSendTime = 0;
let kicked = false;
let chatStatus = 1;
let customText = '';

function scrollToBottom() {
  const msgBox = document.getElementById('chat-messages');
  msgBox.scrollTop = msgBox.scrollHeight;
}

function renderMessage(msg) {
  const isSelf = msg.is_self;
  const side = isSelf ? 'justify-content-end' : 'justify-content-start';
  const bubbleClass = isSelf ? 'bg-primary text-white' : 'bg-light';
  const html = `
    <div class="d-flex ${side} mb-2">
      ${!isSelf ? `<img src="/static/chat/${msg.avatar}" class="rounded-circle me-2" width="32" height="32">` : ''}
      <div>
        <div class="small text-muted">${msg.nickname} <span class="ms-2">${msg.timestamp}</span></div>
        <div class="p-2 rounded ${bubbleClass}" style="max-width: 350px; word-break: break-all;">${emojify(msg.content)}</div>
      </div>
      ${isSelf ? `<img src="/static/chat/${msg.avatar}" class="rounded-circle ms-2" width="32" height="32">` : ''}
    </div>
  `;
  $('#chat-messages').append(html);
  scrollToBottom();
}

function emojify(text) {
  if (window.EmojiConvertor) {
    const emoji = new EmojiConvertor();
    emoji.replace_mode = 'unified';
    emoji.allow_native = true;
    return emoji.replace_emoticons(text);
  }
  return text;
}

function showStatus(msg, type='danger') {
  $('#chat-status').removeClass('text-danger text-success').addClass('text-' + type).text(msg);
}

function updateOnlineCount(count) {
  $('#online-count').text('在线人数: ' + count);
}

function updateUserInfo(user) {
  $('#user-avatar').attr('src', '/static/chat/' + user.avatar);
  $('#user-nickname').text(user.nickname);
  $('#user-gender').text(user.gender);
}

function setChatStatus(status, custom) {
  chatStatus = status;
  customText = custom || '';
  if (status === 0) {
    $('#chat-input-area').hide();
    $('#chatroom-custom-text').text(customText || '聊天室已关闭').show();
  } else if (status === 2) {
    $('#chatroom-custom-text').text(customText || '聊天室仅在指定时间段开放').show();
  } else {
    $('#chatroom-custom-text').hide();
    $('#chat-input-area').show();
  }
}

function kickOffline() {
  kicked = true;
  showStatus('您已被踢下线或禁用聊天室', 'danger');
  $('#chat-input-area').hide();
  $('#nickname-input-area').show();
}

$(function() {
  // 昵称输入
  $('#join-chat').click(function() {
    const nickname = $('#nickname').val().trim();
    if (!nickname) {
      showStatus('请输入昵称');
      return;
    }
    socket = io();
    socket.emit('login', {nickname: nickname});
    socket.on('login_success', function(data) {
      currentUser = data.user;
      $('#nickname-input-area').hide();
      $('#chat-input-area').show();
      $('#chat-messages').empty();
      data.messages.forEach(renderMessage);
      updateUserInfo(currentUser);
      showStatus('欢迎进入聊天室', 'success');
      socket.emit('get_status');
    });
    socket.on('login_error', function(data) {
      showStatus(data.msg);
    });
    socket.on('new_message', function(msg) {
      renderMessage(msg);
    });
    socket.on('send_error', function(data) {
      showStatus(data.msg);
    });
    socket.on('online_count', function(data) {
      updateOnlineCount(data.count);
    });
    socket.on('chat_status', function(data) {
      setChatStatus(data.status, data.custom_text);
    });
    socket.on('logout_success', function() {
      currentUser = null;
      $('#chat-input-area').hide();
      $('#nickname-input-area').show();
      showStatus('已退出聊天室', 'success');
    });
    // 心跳包
    setInterval(function() {
      if (socket && currentUser && !kicked) {
        socket.emit('heartbeat');
      }
    }, 10000);
  });

  // 退出登录
  $('#logout-btn').click(function() {
    if (socket) {
      socket.emit('logout');
      socket.disconnect();
      socket = null;
    }
    currentUser = null;
    $('#chat-input-area').hide();
    $('#nickname-input-area').show();
    showStatus('已退出聊天室', 'success');
  });

  // 发送消息
  $('#send-btn').click(function() {
    if (!socket || !currentUser) return;
    if (chatStatus !== 1) {
      showStatus('聊天室未开放');
      return;
    }
    const now = Date.now();
    if (now - lastSendTime < 10000) {
      showStatus('发送过快，请稍后再试');
      return;
    }
    const content = $('#chat-input').val().trim();
    if (!content) {
      showStatus('消息不能为空');
      return;
    }
    if (content.length > 500) {
      showStatus('消息不能超过500字');
      return;
    }
    socket.emit('send_message', {content: content});
    lastSendTime = now;
    $('#chat-input').val('');
    $('#input-length').text('0');
  });

  // 输入区字数统计
  $('#chat-input').on('input', function() {
    $('#input-length').text($(this).val().length);
  });

  // 回车/ctrl+回车切换
  $('#chat-input').keydown(function(e) {
    if ($('#enter-send').is(':checked')) {
      if (e.key === 'Enter' && !e.ctrlKey) {
        $('#send-btn').click();
        e.preventDefault();
      } else if (e.key === 'Enter' && e.ctrlKey) {
        // 换行
      }
    } else {
      if (e.key === 'Enter' && e.ctrlKey) {
        $('#send-btn').click();
        e.preventDefault();
      }
    }
  });

  // 单选框切换
  $('#enter-send').change(function() {
    enterSend = $(this).is(':checked');
  });
}); 