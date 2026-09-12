# MD Integration

MD Community exposes a high-quality image-to-3D workflow through a local
adapter boundary. The public package contains the contract and planner, not a
model bundle.

## Public Request

The request is a JSON object with these optional fields:

```json
{
  "input_kind": "image",
  "output_format": "glb",
  "quality": "high",
  "texture": false
}
```

`input_kind` is currently `image`. `output_format` is `glb` or `obj`.
`quality` is `balanced` or `high`.

The optional `image_path`, `output_path`, `overwrite`, and `seed` fields are
local-run controls. They are accepted by the CLI runner but are never echoed
in the public result.

## Adapter Protocol

An adapter reads one JSON object from standard input and writes one JSON object
to standard output. It must keep logs on standard error. The request shape is:

```json
{
  "protocol": "md-adapter/1.0",
  "operation": "image_to_3d",
  "input_path": "INPUT_IMAGE",
  "output_dir": "OUTPUT_DIRECTORY",
  "output_format": "glb",
  "quality": "high",
  "texture": false,
  "seed": 1234
}
```

On success, the adapter returns `status: completed` and an `artifact_path`
inside `output_dir`:

```json
{
  "status": "completed",
  "artifact_path": "OUTPUT_DIRECTORY/model.glb",
  "format": "glb"
}
```

The bridge never returns `input_path`, `output_dir`, or `artifact_path` to the
client. Configure a separately installed adapter with `AEGIS_MD_COMMAND` and,
when needed, `AEGIS_MD_CWD`; a JSON array command is preferred because it does
not require shell parsing. The colocated adapter layout is discovered
automatically when the source checkout and the MD installation are placed
together.

## Adapter Rules

- The backend runs locally under the user's own installation and license.
- The adapter must not print its command, local path, address, or credentials.
- The adapter must not receive arbitrary task code.
- Generation requires an explicit human approval step.
- Returned artifacts must be described by a safe logical name, not a machine
  path.
- The bridge accepts only an artifact inside its temporary output area, checks
  the GLB or OBJ structure, and can copy it to an explicitly selected output
  file after verification.
- Private Stable models and optimizers are outside this contract.

## Status And Testing

```powershell
aegis-community md
aegis-community md-plan --input examples/md_request.json --format json
```

`ready` means that a protocol adapter was detected. `optional_backend_not_configured`
means that the public contract is healthy but no adapter has been attached.
Neither result claims that a model generation has completed.

For an approved local run, keep the image and destination in local variables:

```powershell
aegis-community md-run --input examples/md_request.json --image $image --output $output --approve
```

The run is complete only when the command reports `status: completed`,
`read-back: True`, and `saved: True`. The destination must end in `.glb` or
`.obj`; an existing file is not replaced unless `--overwrite` is supplied.

## Licensing

This repository does not relicense an MD backend. Users must review and obey
the backend's own license before installing or distributing it.
