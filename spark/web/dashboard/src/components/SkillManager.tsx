'use client';

export default function SkillManager({ skills }: { skills: any[] }) {
  return (
    <div className="spark-card">
      <h2 className="text-lg font-bold spark-accent mb-4">Learned Skills</h2>
      <div className="space-y-3">
        {skills.map((skill, i) => (
          <div key={i} className="p-3 rounded bg-gray-900">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold">{skill.name}</span>
              <span className="text-sm text-gray-400">{skill.use_count || 0} uses</span>
            </div>
            <div className="text-sm text-gray-400 mb-2">{skill.description}</div>
            <div className="flex items-center gap-4 text-xs">
              <span>Success: <span className="spark-success">{((skill.success_rate || 0) * 100).toFixed(0)}%</span></span>
              <span>Steps: {skill.steps?.length || 0}</span>
              <span>Tags: {skill.tags?.join(', ') || 'none'}</span>
            </div>
            <div className="mt-2 h-1.5 bg-gray-800 rounded overflow-hidden">
              <div
                className="h-full bg-cyan-500 rounded"
                style={{ width: `${(skill.success_rate || 0) * 100}%` }}
              />
            </div>
          </div>
        ))}
        {skills.length === 0 && <div className="text-gray-500">No skills learned yet</div>}
      </div>
    </div>
  );
}
