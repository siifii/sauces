// <x-card>: a surface for a heading, body text and an action (light DOM, no shadow root).
// It labels itself with its heading so screen readers announce the region.
class XCard extends HTMLElement {
  connectedCallback() {
    this.setAttribute("role", "region");
    const heading = this.querySelector("h2, h3");
    if (heading) {
      heading.id ||= `x-card-${Math.random().toString(36).slice(2, 8)}`;
      this.setAttribute("aria-labelledby", heading.id);
    }
  }
}

customElements.define("x-card", XCard);
