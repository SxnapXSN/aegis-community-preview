# Version Matrix

The public and private lines have separate version numbers. A public client
only depends on the public contract and must not infer private capabilities
from a version string.

| Line | Version | Purpose | Publication |
| --- | --- | --- | --- |
| Aegis Contract | `AC 1.0` | Manifest, handshake, capability discovery | Public |
| Aegis Contract | `AC 1.1` | Permission, preflight, evidence, recovery | Public |
| Community | `C 0.1.1` | Previous contract-only preview | Legacy |
| Community | `C 0.5.0` | Bootstrap, Bridge, and auto-connect beta | Planned |
| Community | `C 0.8.0` | Integration candidate with MD contract | Previous candidate |
| Community | `C 1.0.0` | First fully verified free release | Previous candidate |
| Community | `C 1.1.0` | Universal documents, AI context packs, and bounded folder ingestion | Current public preview |
| Community | `C 1.1.x` | Client compatibility and reliability | Planned |
| Community | `C 1.2.x` | Diagnostics, repair, evidence, and MD quality | Planned |
| Community | `C 1.5.0` | More public safe workflows | Planned |
| Community | `C 2.0.0` | Breaking public contract or runtime change | Future |
| MD Community | `MD-C 1.0.0` | High-quality public MD capability | Reserved |
| MD Community | `MD-C 1.1.x` | Presets and quality improvements | Planned |
| MD Community | `MD-C 1.2.x` | Batch, cache, and queue improvements | Planned |
| MD Community | `MD-C 1.5.0` | Advanced sandboxed public workflow | Planned |
| MD Community | `MD-C 2.0.0` | Breaking MD contract change | Future |
| Stable Private | `S-R1.x` | Private control plane and secret updates | Private |
| Stable Private | `S-R2.x` | Next private architecture | Private |
| MD Private | `MD-X` | Private models, optimizers, and pipelines | Private |

`C 1.1.0` is the current public preview line. Its public availability does
not imply access to the private Stable engine or private capabilities.
