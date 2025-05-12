// 骨架屏和真实内容切换
window.addEventListener('DOMContentLoaded', function() {
  var skeleton = document.getElementById('skeleton');
  var realContent = document.getElementById('real-content');
  if (skeleton && realContent) {
    setTimeout(function() {
      skeleton.style.display = 'none';
      realContent.style.display = 'block';
    }, 600); // 可根据实际加载速度调整
  }

  // 图片懒加载
  var imgs = document.querySelectorAll('img.lazy-img[data-src]');
  if ('IntersectionObserver' in window) {
    let observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          let img = entry.target;
          img.src = img.dataset.src;
          img.onload = function() { img.classList.add('loaded'); };
          img.removeAttribute('data-src');
          obs.unobserve(img);
        }
      });
    });
    imgs.forEach(img => observer.observe(img));
  } else {
    imgs.forEach(img => { img.src = img.dataset.src; img.classList.add('loaded'); });
  }

  // 页面淡入动画
  var main = document.getElementById('main-content');
  if (main) {
    main.classList.add('fade-in');
  }
});

// loading 动画控制（可在ajax请求前后调用）
function showLoading() {
  var spinner = document.getElementById('loading-spinner');
  if (spinner) spinner.style.display = 'block';
}
function hideLoading() {
  var spinner = document.getElementById('loading-spinner');
  if (spinner) spinner.style.display = 'none';
} 