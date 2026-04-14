import { useState, useEffect } from 'react';
import { X, AlertTriangle, CheckCircle, BarChart2, Loader } from 'lucide-react';
import { api } from '../services/api';
import '../index.css';

export default function HallucinationPanel({ onClose }) {
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const load = async () => {
            try {
                const data = await api.get('/hallucination-report');
                setReport(data);
            } catch (e) {
                setError('Não foi possível carregar o relatório.');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    const hallucinationRate = report
        ? report.total_classified > 0
            ? Math.round((report.total_hallucinated / report.total_classified) * 100)
            : 0
        : 0;

    return (
        <div className="panel-overlay" onClick={onClose}>
            <div className="hallucination-panel glass-panel" onClick={e => e.stopPropagation()}>
                <div className="panel-header">
                    <div className="panel-title">
                        <BarChart2 size={20} className="panel-icon" />
                        <h2>Relatório de Alucinações</h2>
                    </div>
                    <button className="icon-btn" onClick={onClose} title="Fechar">
                        <X size={20} />
                    </button>
                </div>

                {loading && (
                    <div className="panel-loading">
                        <Loader size={28} className="spin" />
                        <p>Carregando relatório...</p>
                    </div>
                )}

                {error && (
                    <div className="panel-error">{error}</div>
                )}

                {report && !loading && (
                    <>
                        {/* Stat Cards */}
                        <div className="stat-cards">
                            <div className="stat-card">
                                <span className="stat-number">{report.total_classified}</span>
                                <span className="stat-label">Total Classificados</span>
                            </div>
                            <div className="stat-card bad">
                                <AlertTriangle size={18} />
                                <span className="stat-number">{report.total_hallucinated}</span>
                                <span className="stat-label">Alucinações</span>
                            </div>
                            <div className="stat-card good">
                                <CheckCircle size={18} />
                                <span className="stat-number">{report.total_correct}</span>
                                <span className="stat-label">Respostas Corretas</span>
                            </div>
                            <div className={`stat-card ${hallucinationRate > 30 ? 'bad' : 'neutral'}`}>
                                <span className="stat-number">{hallucinationRate}%</span>
                                <span className="stat-label">Taxa de Alucinação</span>
                            </div>
                        </div>

                        {/* Table */}
                        <div className="panel-section-title">
                            <AlertTriangle size={15} />
                            Respostas marcadas como incorretas ({report.total_hallucinated})
                        </div>

                        {report.hallucinations.length === 0 ? (
                            <div className="panel-empty">
                                <CheckCircle size={32} className="good-icon" />
                                <p>Nenhuma alucinação registrada ainda.</p>
                                <span>Quando você marcar uma resposta como incorreta, ela aparecerá aqui.</span>
                            </div>
                        ) : (
                            <div className="hallucination-table-wrapper">
                                <table className="hallucination-table">
                                    <thead>
                                        <tr>
                                            <th>Conversa</th>
                                            <th>Pergunta do Usuário</th>
                                            <th>Resposta da IA (resumo)</th>
                                            <th>Classificação</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {report.hallucinations.map(row => (
                                            <tr key={row.message_id}>
                                                <td>
                                                    <span className="conv-title-pill">{row.conversation_title}</span>
                                                </td>
                                                <td className="question-cell">{row.user_question}</td>
                                                <td className="response-cell">{row.ai_response_summary}</td>
                                                <td>
                                                    <span className="badge badge-bad">⚠ Incorreto</span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
