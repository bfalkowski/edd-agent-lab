# Frontend Style Guide

This guide captures the current EDD Agent Lab builder style so new frontend
work feels consistent with the application instead of becoming a collection of
one-off screens.

The builder should feel like a quiet local workspace for designing agents with
evaluation evidence. It should be direct, editable, and calm. Prefer product
surfaces that help a developer understand and change the draft over surfaces
that explain the product back to them.

## Core Principles

1. Put the work first.
   The first visible surface should be the active draft, workflow, artifact, or
   editor. Avoid marketing-style sections, decorative panels, and explanatory
   hero content.

2. Use human labels, not implementation labels.
   Show `Eval Contract`, not `eval_contract`. Show `Rules`, not
   `behavior-rules.yaml`. File names can exist in export/download/debug
   surfaces, but they should not be the primary workflow language.

3. Keep navigation meaningful.
   A control should either navigate, act, or edit. Avoid fake breadcrumbs,
   repeated current-step summaries, and labels that cannot be clicked.

4. Keep status local.
   Streaming activity, progress text, retries, and failures belong on the step
   or artifact that produced them. Do not create a global activity column for
   local step work.

5. Prefer editing over raw text when structure is known.
   YAML is the storage format, not the default UI. Use structured forms for
   targets, rules, metrics, gates, requirements, tools, and graph elements.

## Layout

The app has three primary regions:

- left agent rail
- center workflow workspace
- right artifact review drawer

Use the left rail for draft selection and draft-level actions. Use the center
workspace for the workflow and generated artifact rows. Use the right drawer
for focused review and editing.

Do not duplicate the selected agent name or workflow status inside the center
workspace when it already appears in the top bar or workflow cards.

## Left Rail

The left rail owns draft-level navigation and actions.

- Product name appears at the top when expanded.
- Collapsed rail shows only the product mark and the panel toggle.
- Agent rows show the draft name.
- Draft actions live behind the row ellipsis.
- Use an inline menu for rename, export, archive, and delete.
- Delete should use a confirmation dialog.

Avoid keyboard badges, decorative window controls, folder labels that do not add
meaning, and permanent inline action icons on every row.

## Center Workflow

The center workspace is the builder's main working surface.

Workflow cards should show:

- step name
- compact step status
- current action when the step can run
- generated artifact rows
- local activity or retry context only when relevant

Artifact rows should show:

- human artifact name
- short purpose or description
- a consistent `Review` button

Do not show artifact file names in the main workflow. Do not show a fixed step
count as a primary progress model, because future drafts may add v2, v3, and
additional loops.

## Right Review Drawer

The right drawer is an editor, not a control room.

Header rules:

- Title is the human artifact name.
- Use an icon-only panel close/toggle.
- Use `Save`, not `Save edits`.
- Disable `Save` when there are no unsaved changes.
- Do not include `Review artifact`, `Edit`, `Diff`, or whole-artifact `Delete`
  in the default header.

Editor rules:

- Show structured controls when the artifact shape is known.
- Show raw YAML only for artifacts without a structured editor.
- Show validation only when there are issues.
- Do not show a success banner such as `Artifact shape looks valid`.

Repeated sections need local add/remove controls. New items should insert at
the top of the list and visibly highlight so the click has immediate feedback.

## Buttons And Controls

Buttons should use short verb labels.

Preferred labels:

- `Review`
- `Save`
- `Create draft`
- `Generate design`
- `Run v0`
- `Evaluate v0`
- `Publish`

Avoid verbose labels when the context is already clear. For example, use
`Save`, not `Save edits`, inside an artifact editor.

Use icon-only buttons for panel toggles and compact chrome. Include accessible
labels and titles for icon-only controls.

## Copy

Copy should be practical and compact.

Use copy for:

- artifact purpose
- action labels
- error and retry context
- empty states
- confirmation dialogs

Avoid copy that restates obvious UI state. For example, if the active workflow
card is `Evaluate v0`, do not also show a separate banner saying
`Evaluate v0 and generate a failure packet`.

## Visual Language

The visual system is quiet and mostly neutral.

- Backgrounds are white or very light neutral.
- Borders are subtle.
- Cards are shallow and functional.
- Border radius should stay modest.
- Avoid dark blocks, green success floods, heavy gradients, decorative blobs,
  and saturated one-color themes.

Use emphasis sparingly:

- dark filled buttons for primary actions
- red only for destructive confirmation
- muted gray for secondary metadata
- small transient highlights for newly added editor sections

## Validation And Errors

Only show validation UI when something needs attention.

- Validation issues appear in the review drawer.
- Step failures appear on the owning step.
- Publish retry context appears on the publish step.
- Global errors should be reserved for failures that block the whole workspace.

## Future Projects

For future EDD apps, reuse the same interaction model when the domain is a
developer workspace:

```text
project rail -> active workspace -> focused review/edit drawer
```

Use this pattern for tools that manage local drafts, generated artifacts,
evidence, or publishable payloads. If a future project is operational or
developer-facing, prefer dense but readable work surfaces over landing pages,
hero sections, or decorative dashboards.

When adding a new component, ask:

1. Does it expose the work directly?
2. Does it use human labels?
3. Does it keep status local?
4. Does it avoid duplicating information already visible nearby?
5. Does it provide clear feedback after an action?

If the answer is no, simplify before adding more UI.
