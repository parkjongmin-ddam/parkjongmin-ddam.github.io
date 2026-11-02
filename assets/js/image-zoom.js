/*
 * 본문 이미지 확대 보기
 * - .page__content 안의 이미지를 클릭하면 오버레이로 표시 (화면 맞춤)
 * - 오버레이에서 이미지를 클릭하면 원본 크기 ↔ 화면 맞춤 전환 (원본 크기는 스크롤로 이동)
 * - 배경 클릭 / Esc: 닫기, ← →: 이전·다음 이미지
 * - 제외: 링크 안의 이미지, class="no-zoom", 가로 80px 미만 이미지
 */
(function () {
  var content = document.querySelector(".page__content");
  if (!content) return;

  var MIN_WIDTH = 80;
  var images = [];
  var current = -1;
  var overlay, stage, img, caption, counter;

  function eligible(el) {
    if (el.closest("a")) return false;
    if (el.classList.contains("no-zoom")) return false;
    return (el.naturalWidth || el.width) >= MIN_WIDTH;
  }

  function build() {
    overlay = document.createElement("div");
    overlay.className = "iz-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", "이미지 확대 보기");
    overlay.innerHTML =
      '<div class="iz-stage"><img class="iz-img" alt=""></div>' +
      '<div class="iz-bar">' +
      '<span class="iz-caption"></span>' +
      '<span class="iz-counter"></span>' +
      '<button type="button" class="iz-btn iz-prev" aria-label="이전 이미지">&#8249;</button>' +
      '<button type="button" class="iz-btn iz-next" aria-label="다음 이미지">&#8250;</button>' +
      '<button type="button" class="iz-btn iz-close" aria-label="닫기">&times;</button>' +
      "</div>";
    document.body.appendChild(overlay);

    stage = overlay.querySelector(".iz-stage");
    img = overlay.querySelector(".iz-img");
    caption = overlay.querySelector(".iz-caption");
    counter = overlay.querySelector(".iz-counter");

    img.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleFull(e);
    });
    stage.addEventListener("click", function (e) {
      if (e.target === stage) close();
    });
    overlay.querySelector(".iz-close").addEventListener("click", close);
    overlay.querySelector(".iz-prev").addEventListener("click", function () { step(-1); });
    overlay.querySelector(".iz-next").addEventListener("click", function () { step(1); });
  }

  function toggleFull(e) {
    var full = !overlay.classList.contains("iz-full");
    // 원본이 화면보다 작으면 전환할 의미가 없음
    if (full && img.naturalWidth <= stage.clientWidth && img.naturalHeight <= stage.clientHeight) return;

    // 클릭 지점 비율을 기억했다가 원본 크기에서 그 지점이 보이도록 스크롤
    var rect = img.getBoundingClientRect();
    var rx = (e.clientX - rect.left) / rect.width;
    var ry = (e.clientY - rect.top) / rect.height;

    overlay.classList.toggle("iz-full", full);
    if (full) {
      stage.scrollLeft = img.offsetLeft + img.offsetWidth * rx - stage.clientWidth / 2;
      stage.scrollTop = img.offsetTop + img.offsetHeight * ry - stage.clientHeight / 2;
    } else {
      stage.scrollLeft = 0;
      stage.scrollTop = 0;
    }
  }

  function show(i) {
    current = (i + images.length) % images.length;
    var src = images[current];
    overlay.classList.remove("iz-full");
    stage.scrollLeft = 0;
    stage.scrollTop = 0;
    img.src = src.currentSrc || src.src;
    img.alt = src.alt || "";
    caption.textContent = src.alt || "";
    counter.textContent = images.length > 1 ? current + 1 + " / " + images.length : "";
    overlay.classList.toggle("iz-single", images.length < 2);
  }

  function open(el) {
    images = Array.prototype.filter.call(content.querySelectorAll("img"), eligible);
    var i = images.indexOf(el);
    if (i < 0) return;
    if (!overlay) build();
    show(i);
    overlay.classList.add("iz-open");
    document.documentElement.classList.add("iz-lock");
    document.addEventListener("keydown", onKey);
  }

  function close() {
    overlay.classList.remove("iz-open", "iz-full");
    document.documentElement.classList.remove("iz-lock");
    document.removeEventListener("keydown", onKey);
    img.removeAttribute("src");
  }

  function step(d) {
    if (images.length > 1) show(current + d);
  }

  function onKey(e) {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowLeft") step(-1);
    else if (e.key === "ArrowRight") step(1);
  }

  function mark(el) {
    if (eligible(el)) el.classList.add("iz-zoomable");
  }

  Array.prototype.forEach.call(content.querySelectorAll("img"), function (el) {
    if (el.complete) mark(el);
    else el.addEventListener("load", function () { mark(el); }, { once: true });
  });

  content.addEventListener("click", function (e) {
    var el = e.target;
    if (el.tagName === "IMG" && eligible(el)) {
      e.preventDefault();
      open(el);
    }
  });
})();
