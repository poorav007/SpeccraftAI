import { describe, expect, it } from "vitest";
import { SAMPLE_SHOP_V1 } from "../src/config/sampleSpecs.js";
import { buildHandoffHtml, escapeHtml } from "../src/utils/fileHelpers.js";

describe("White-label Client Handoff HTML/PDF export helpers", () => {
  it("escapes HTML special characters to prevent XSS in generated handoff reports", () => {
    const escaped = escapeHtml(`<script>alert("xss")</script> & 'quote'`);
    expect(escaped).toBe("&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt; &amp; &#39;quote&#39;");
  });

  it("renders custom brandName, @media print rules, and escapes docstring payloads", () => {
    const dirtySpec = {
      ...SAMPLE_SHOP_V1,
      info: {
        ...SAMPLE_SHOP_V1.info,
        title: "Shop <Admin>",
        description: `<img src=x onerror="alert(1)">`,
      },
    };

    const html = buildHandoffHtml(dirtySpec, { is_valid: true, errors: [], warnings: [] }, "Acme Agency");
    expect(html).toContain("Acme Agency");
    expect(html).toContain("Shop &lt;Admin&gt;");
    expect(html).not.toContain(`<img src=x onerror="alert(1)">`);
    expect(html).toContain("@media print");
    expect(html).toContain("window.print()");
  });
});

