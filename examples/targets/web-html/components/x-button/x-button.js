// <x-button>: enhances the <button> inside it (light DOM). The `busy` attribute disables it.
class XButton extends HTMLElement {
  static observedAttributes = ["busy"];

  attributeChangedCallback() {
    const button = this.querySelector("button");
    if (!button) return;
    button.disabled = this.hasAttribute("busy");
    button.setAttribute("aria-busy", String(this.hasAttribute("busy")));
  }

  connectedCallback() {
    this.attributeChangedCallback();
  }
}

customElements.define("x-button", XButton);
