// 聊天室后台管理前端逻辑
$(function() {
  // 聊天室状态
  function loadChatConfig() {
    $.get('/admin/api/chat/config', function(data) {
      $('#chat-status-select').val(data.status);
      $('#chat-open-time').val(data.open_time);
      $('#chat-close-time').val(data.close_time);
      $('#chat-custom-text').val(data.custom_text);
      $('#chat-expected-open-time').val(data.expected_open_time);
    });
  }
  $('#chat-status-form').submit(function(e) {
    e.preventDefault();
    const data = {
      status: $('#chat-status-select').val(),
      open_time: $('#chat-open-time').val(),
      close_time: $('#chat-close-time').val(),
      custom_text: $('#chat-custom-text').val(),
      expected_open_time: $('#chat-expected-open-time').val()
    };
    $.ajax({url:'/admin/api/chat/config', type:'POST', contentType:'application/json', data:JSON.stringify(data), success:function(){loadChatConfig();alert('保存成功')}});
  });
  loadChatConfig();

  // 敏感词管理
  function loadSensitiveWords() {
    $.get('/admin/api/chat/sensitive', function(data) {
      $('#sensitive-list').empty();
      data.forEach(function(w) {
        $('#sensitive-list').append(`<li class="list-group-item d-flex justify-content-between align-items-center">${w.word}<button class="btn btn-sm btn-danger del-sensitive" data-id="${w.id}"><i class="bi bi-trash"></i></button></li>`);
      });
    });
  }
  $('#add-sensitive-form').submit(function(e) {
    e.preventDefault();
    const word = $('#new-sensitive-word').val().trim();
    if (!word) return;
    $.ajax({url:'/admin/api/chat/sensitive',type:'POST',contentType:'application/json',data:JSON.stringify({word:word}),success:function(){loadSensitiveWords();$('#new-sensitive-word').val('')}});
  });
  $('#sensitive-list').on('click', '.del-sensitive', function() {
    const id = $(this).data('id');
    $.ajax({url:'/admin/api/chat/sensitive/'+id,type:'DELETE',success:loadSensitiveWords});
  });
  loadSensitiveWords();

  // 黑名单管理
  function loadBlacklist() {
    $.get('/admin/api/chat/blacklist', function(data) {
      $('#blacklist-list').empty();
      data.forEach(function(u) {
        $('#blacklist-list').append(`<li class="list-group-item d-flex justify-content-between align-items-center">${u.nickname} (${u.ip})<span>${u.reason||''}</span><button class="btn btn-sm btn-danger del-blacklist" data-id="${u.id}"><i class="bi bi-trash"></i></button></li>`);
      });
    });
  }
  $('#blacklist-list').on('click', '.del-blacklist', function() {
    const id = $(this).data('id');
    $.ajax({url:'/admin/api/chat/blacklist/'+id,type:'DELETE',success:loadBlacklist});
  });
  loadBlacklist();

  // 消息管理
  function loadMessages() {
    $.get('/admin/api/chat/messages', function(data) {
      $('#messages-list').empty();
      data.forEach(function(m) {
        $('#messages-list').append(`<li class="list-group-item d-flex justify-content-between align-items-center"><span>${m.nickname}: ${m.content}</span><span>${m.timestamp}</span><button class="btn btn-sm btn-danger del-message" data-id="${m.id}"><i class="bi bi-trash"></i></button></li>`);
      });
    });
  }
  $('#messages-list').on('click', '.del-message', function() {
    const id = $(this).data('id');
    $.ajax({url:'/admin/api/chat/messages/'+id,type:'DELETE',success:loadMessages});
  });
  loadMessages();

  // 用户管理
  function loadUsers() {
    $.get('/admin/api/chat/users', function(data) {
      $('#users-list').empty();
      data.forEach(function(u) {
        $('#users-list').append(`<li class="list-group-item d-flex justify-content-between align-items-center">${u.nickname} (${u.ip})<span>${u.last_active_time}</span><span>${u.last_msg||''}</span>${u.is_blacklisted?'<span class=\'badge bg-danger\'>已拉黑</span>':'<button class=\'btn btn-sm btn-warning add-blacklist\' data-id="'+u.id+'">拉黑</button>'}</li>`);
      });
    });
  }
  $('#users-list').on('click', '.add-blacklist', function() {
    const id = $(this).data('id');
    const reason = prompt('请输入拉黑原因');
    if (!reason) return;
    $.ajax({url:'/admin/api/chat/blacklist',type:'POST',contentType:'application/json',data:JSON.stringify({user_id:id,reason:reason}),success:()=>{loadUsers();loadBlacklist();}});
  });
  loadUsers();
}); 