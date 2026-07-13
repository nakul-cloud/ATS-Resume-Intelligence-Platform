import React, { useState, useEffect } from 'react';
import { recruiterApi } from '../../api/recruiterApi';
import { Card } from '../../components/common/Card';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Toast } from '../../components/common/Toast';

export const MetricsPage = () => {
  const [metrics, setMetrics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await recruiterApi.getMetrics();
        // Backend returns response format with key_metrics, domain_distribution etc.
        setMetrics(response);
      } catch (err) {
        console.error(err);
        setToastMessage('Failed to fetch dashboard metrics.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-xl" />;
  }

  const keyMetrics = metrics?.key_metrics || {};
  const perfMetrics = metrics?.performance_metrics || {};
  const domainDist = metrics?.domain_distribution || {};

  const cards = [
    { label: 'Total Candidates Indexed', value: keyMetrics.total_candidates ?? 0, icon: 'groups', color: 'text-primary' },
    { label: 'Avg Experience', value: `${keyMetrics.avg_experience_years?.toFixed(1) || '0'} Yrs`, icon: 'history_edu', color: 'text-green-600' },
    { label: 'Unique Skills', value: keyMetrics.unique_skills ?? 0, icon: 'schema', color: 'text-amber-500' },
    { label: 'System Uptime Status', value: `${perfMetrics.uptime_percentage || 99.9}%`, icon: 'cloud_done', color: 'text-blue-500' }
  ];

  return (
    <div className="space-y-lg">
      <h2 className="font-h2 text-h2 text-primary font-bold">Metrics Dashboard</h2>
      
      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-md">
        {cards.map((card, index) => (
          <Card key={index} variant="raised" className="flex items-center gap-md">
            <div className={`w-12 h-12 rounded-xl bg-surface-container-high flex items-center justify-center border border-outline-variant/30 ${card.color}`}>
              <span className="material-symbols-outlined text-2xl">{card.icon}</span>
            </div>
            <div>
              <span className="text-[10px] uppercase tracking-wider text-outline font-label-caps font-semibold block">
                {card.label}
              </span>
              <span className="text-2xl font-bold text-on-surface">{card.value}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-lg">
        {/* Domain Distribution */}
        <div className="lg:col-span-6">
          <Card variant="raised" className="space-y-md h-full">
            <h3 className="font-h3 text-primary font-semibold border-b border-outline-variant pb-xs">
              Candidate Domain Distribution
            </h3>
            {Object.keys(domainDist).length > 0 ? (
              <div className="space-y-sm pt-xs">
                {Object.entries(domainDist).map(([domain, count], idx) => (
                  <div key={idx} className="flex justify-between items-center bg-surface-container-low p-sm rounded-xl border border-outline-variant/30">
                    <span className="text-sm font-semibold text-on-surface capitalize">{domain}</span>
                    <span className="bg-primary-container text-white px-3 py-1 rounded-full text-xs font-bold font-mono">
                      {count} Profiles
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-outline font-medium">No domain distribution data available.</p>
            )}
          </Card>
        </div>

        {/* System Latency & Details */}
        <div className="lg:col-span-6">
          <Card variant="raised" className="space-y-md h-full">
            <h3 className="font-h3 text-primary font-semibold border-b border-outline-variant pb-xs">
              Performance Status Metrics
            </h3>
            <div className="space-y-sm pt-xs text-sm">
              <div className="flex justify-between p-sm rounded-xl border border-outline-variant/20">
                <span className="text-on-surface-variant font-medium">Model Embeddings Provider</span>
                <span className="font-mono font-semibold">SentenceTransformer / BGE Large</span>
              </div>
              <div className="flex justify-between p-sm rounded-xl border border-outline-variant/20">
                <span className="text-on-surface-variant font-medium">AI Parsing Engine</span>
                <span className="font-mono font-semibold">Groq LLM (LLaMA3-8B)</span>
              </div>
              <div className="flex justify-between p-sm rounded-xl border border-outline-variant/20">
                <span className="text-on-surface-variant font-medium">Vector Database</span>
                <span className="font-mono font-semibold">Qdrant Cloud (Indexed matches)</span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {toastMessage && (
        <Toast 
          message={toastMessage} 
          type="error" 
          onClose={() => setToastMessage(null)} 
        />
      )}
    </div>
  );
};
