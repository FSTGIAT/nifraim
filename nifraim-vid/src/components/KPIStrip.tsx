import { KPICard } from './KPICard';

interface KPIItem {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  color: string;
}

interface KPIStripProps {
  items: KPIItem[];
  baseDelay?: number;
  stagger?: number;
}

export const KPIStrip: React.FC<KPIStripProps> = ({
  items,
  baseDelay = 0,
  stagger = 4,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        gap: 24,
        justifyContent: 'center',
        flexWrap: 'nowrap',
      }}
    >
      {items.map((item, i) => (
        <KPICard
          key={item.label}
          label={item.label}
          value={item.value}
          prefix={item.prefix}
          suffix={item.suffix}
          color={item.color}
          delay={baseDelay + i * stagger}
        />
      ))}
    </div>
  );
};
