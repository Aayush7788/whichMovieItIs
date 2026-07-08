export function SectionHeader({
  eyebrow,
  title,
  description,
  actionLabel,
  onActionClick,
}) {
  return (
    <div className="section-header">
      <div>
        {eyebrow && <p className="section-eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>

      {actionLabel && (
        <button
          type="button"
          className="text-action"
          onClick={onActionClick}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
