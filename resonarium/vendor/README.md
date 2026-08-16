# Vendored libraries

Third-party code, committed deliberately rather than fetched at runtime.

| File | Version | License | Upstream |
|---|---|---|---|
| `three.min.js` | r134 | MIT (Copyright 2010–2021 Three.js Authors) | `cdnjs.cloudflare.com/ajax/libs/three.js/r134/three.min.js` |

`resonarium_hologram_cymatic_nodal_4D.html` loaded this from a CDN, which meant it did
not render with the network off and announced the reader's IP address to Cloudflare on
every launch. Six hundred kilobytes in the repository buys back both, and buys back the
guarantee that the instrument will still open in ten years when that CDN path has moved.

The file is byte-for-byte the upstream distribution, including its licence header:

    sha256  74782bdbcf6518f7745ed77035968fcae95ed4ab5c9a0f90cf646a69c20785ec

Verify with `sha256sum vendor/three.min.js`. Do not edit it — patch at the call site.
