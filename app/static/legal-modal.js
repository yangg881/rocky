/**
 * Zhida Resume Legal Terms, Privacy Policy & ICP Footer Manager
 */
(function() {
  const legalData = {
    terms: {
      title: "用户服务协议",
      content: `
        <h3>1. 服务条款的确认与接受</h3>
        <p>本协议是用户（以下简称“您”）与职达简历平台（以下简称“本平台”）之间关于使用本平台AI简历优化、岗位适配、简历导出及相关服务所订立的法律协议。当您注册账号、登录或使用本平台提供的任何服务时，即表示您已充分阅读、理解并同意受本协议约束。</p>

        <h3>2. 账号注册与安全</h3>
        <p>2.1 用户须提供真实、准确、有效的手机号码或账号信息完成注册。一个手机号仅可绑定一个主账号。</p>
        <p>2.2 您有责任妥善保管账号及登录凭证的安全。因您保管不善、泄露账号信息或将账号出借他人使用所导致的任何损失与后果，均由您自行承担。</p>

        <h3>3. AI 服务使用规范</h3>
        <p>3.1 本平台基于人工智能技术，为用户提供个人履历润色、表达优化、岗位匹配度分析及 Word/PDF 导出服务。</p>
        <p>3.2 您承诺在平台填写的教育经历、工作经验、项目业绩等均基于真实事实。不得利用本平台生成或编造虚假履历、伪造身份文件、发表违法违规言论或侵犯他人合法权益。</p>
        <p>3.3 禁止对本平台服务进行反向工程、恶意爬取、攻击服务器或利用自动化工具非法调用 API 接口。</p>

        <h3>4. 知识产权声明</h3>
        <p>4.1 本平台的软件代码、UI 界面设计、商标标识、AI 适配算法及相关技术文档的知识产权均归本平台所有。</p>
        <p>4.2 您对根据自身真实经历生成的简历文本内容享有合法的个人使用权与导出保存权。</p>

        <h3>5. 服务变更、中断与终止</h3>
        <p>5.1 本平台有权根据技术升级、业务发展或法律法规调整的需要，变更、暂停或终止部分或全部服务。</p>
        <p>5.2 对于违反本协议法律法规或恶意攻击系统的用户，本平台有权冻结或封禁其账号，并保留追究相关法律责任的权利。</p>
      `
    },
    privacy: {
      title: "隐私保护政策",
      content: `
        <h3>1. 信息的收集范围</h3>
        <p>为向您提供精准的简历优化与岗位推荐服务，我们可能收集以下信息：</p>
        <ul>
          <li><strong>账号基础信息：</strong>注册手机号、用户名、登录密码凭证、会话凭证。</li>
          <li><strong>职业履历资料：</strong>姓名、联系方式、教育背景、工作经历、技能特长、项目业绩及您上传的简历附件。</li>
          <li><strong>使用与偏好数据：</strong>岗位偏好、搜索关键词、收藏记录及系统操作日志。</li>
        </ul>

        <h3>2. 信息的使用目的</h3>
        <p>我们收集的信息将仅用于以下合法用途：</p>
        <ul>
          <li>为您提供个人简历在线编辑、AI 语言表达润色与格式导出；</li>
          <li>根据您的职业经历进行岗位雷达智能化匹配与优势诊断；</li>
          <li>完成账号身份验证、密码重置及系统安全风控检测；</li>
          <li>提升平台算法精度与优化产品用户体验。</li>
        </ul>

        <h3>3. 数据存储与安全保障</h3>
        <p>3.1 我们采用符合业界高标准的 TLS/SSL 传输加密协议，确保您的简历数据在网络传输过程中的机密性。</p>
        <p>3.2 简历文件与数据库存储于高安全级别的云端加密存储集群中，设置严格的访问控制与防火墙规则，防止未授权访问或数据泄露。</p>

        <h3>4. 信息的共享与第三方披露</h3>
        <p>4.1 未经您的明确授权或许可，我们绝不会将您的个人隐私信息、联系方式或履历明细出售、出租或共享给任何第三方广告服务商。</p>
        <p>4.2 仅在国家司法机关或行政执法部门依照法定程序调取时，我们方依法配合提供。</p>

        <h3>5. 用户的隐私权利</h3>
        <p>您随时有权在工作台中查看、修改、更新或清空删除您的简历数据。若需销毁账号或删除云端所有备份，可向平台提交申请。</p>
      `
    },
    disclaimer: {
      title: "免责与备案声明",
      content: `
        <h3>1. AI 辅助生成结果免责</h3>
        <p>1.1 本平台提供的简历诊断、描述优化及岗位匹配度分析系基于人工智能大语言模型算法生成，结果仅供求职参考。</p>
        <p>1.2 用户在将简历投递至招聘单位前，务必仔细核对简历内容的准确性与真实性。因最终简历投递产生的求职结果与法律责任由用户自行承担。</p>

        <h3>2. 求职效果不承诺说明</h3>
        <p>本平台旨在通过 AI 技术提高简历撰写质量与效率，但不承诺或保证用户使用本服务后必然获得特定的面试机会、求职成功率或薪资水平。</p>

        <h3>3. 系统的可用性与不可抗力</h3>
        <p>因电信骨干网络故障、电力中断、黑客攻击、软硬件升级维护或不可抗力等因素导致的服务中断或延迟，本平台将在合理范围内积极组织抢修，但不承担因此产生的衍生损害赔偿责任。</p>

        <h3>4. 网站 ICP 备案说明</h3>
        <p>本平台严格遵守《中华人民共和国网络安全法》、《互联网信息服务管理办法》等法律法规，完成工信部全国互联网安全管理备案。</p>
        <p><strong>网站备案号：</strong><a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">桂ICP备2026015630号-1</a></p>
        <p><strong>版权所有：</strong>© 2026 职达简历 (Zhida Resume) 版权所有。</p>
      `
    }
  };

  function openLegalModal(type) {
    const data = legalData[type];
    if (!data) return;

    let overlay = document.getElementById("zhida-legal-modal");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "zhida-legal-modal";
      overlay.className = "zhida-legal-overlay";
      overlay.innerHTML = `
        <div class="zhida-legal-box">
          <div class="zhida-legal-head">
            <h2 id="zhida-legal-title"></h2>
            <button type="button" class="zhida-legal-close" id="zhida-legal-close-btn">&times;</button>
          </div>
          <div class="zhida-legal-body" id="zhida-legal-body"></div>
          <div class="zhida-legal-foot">
            <button type="button" class="zhida-legal-confirm" id="zhida-legal-ok-btn">我已阅读并同意</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);

      const close = () => overlay.classList.remove("is-open");
      overlay.querySelector("#zhida-legal-close-btn").onclick = close;
      overlay.querySelector("#zhida-legal-ok-btn").onclick = close;
      overlay.onclick = (e) => { if (e.target === overlay) close(); };
    }

    document.getElementById("zhida-legal-title").textContent = data.title;
    document.getElementById("zhida-legal-body").innerHTML = data.content;
    overlay.classList.add("is-open");
  }

  function mountFooter() {
    if (document.getElementById("zhida-global-footer")) return;

    const footer = document.createElement("footer");
    footer.id = "zhida-global-footer";
    footer.className = "zhida-global-footer";
    footer.innerHTML = `
      <div class="zhida-footer-inner">
        <!-- Brand strip + copyright merged into one line -->
        <div class="zhida-footer-brand">
          <strong class="zhida-footer-brand-name">职达简历</strong>
          <span class="zhida-footer-brand-tag">AI 岗位适配 · 简历优化 · 求职推进</span>
          <span class="zhida-footer-copy">© 2026 职达简历 All Rights Reserved.</span>
        </div>
        <!-- Navigation links -->
        <nav class="zhida-footer-nav" aria-label="法律信息">
          <button type="button" class="zhida-footer-btn" data-legal="terms">用户服务协议</button>
          <span class="zhida-footer-dot" aria-hidden="true">•</span>
          <button type="button" class="zhida-footer-btn" data-legal="privacy">隐私保护政策</button>
          <span class="zhida-footer-dot" aria-hidden="true">•</span>
          <button type="button" class="zhida-footer-btn" data-legal="disclaimer">免责与备案声明</button>
        </nav>
      </div>
    `;
    document.body.appendChild(footer);

    // Bind all [data-legal] elements (footer + any other consent text in the page)
    document.querySelectorAll("[data-legal]").forEach(btn => {
      if (btn.dataset.legalBound) return;  // avoid double-binding
      btn.dataset.legalBound = "1";
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        openLegalModal(btn.getAttribute("data-legal"));
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountFooter);
  } else {
    mountFooter();
  }

  setInterval(mountFooter, 2000);
})();
