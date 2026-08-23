import pathlib
import re

p = pathlib.Path('templates/index.html')
text = p.read_text(encoding='utf-8')

# The exact old block to replace
old_block = """                if (ai.status === 'needs_info' && ai.actionable_requests) {
                    ai.actionable_requests.forEach(req => {
                        replyHtml += `
                        <div class="cmd-request">
                            <div class="device-badge">Device: ${req.device}</div>
                            <div><em>Reason: ${req.reason}</em></div>
                            <code>${req.command}</code>
                        </div>`;
                        memoryString += `\\nRequested ${req.command} on ${req.device}`;
                    });
                } else if (ai.status === 'solution' && ai.faults) {
                    ai.faults.forEach((fault, idx) => {
                        replyHtml += `
                        <div class="fault-card">
                            <h3 style="margin-top:0; color:var(--accent)">Root Cause Found (Layer ${fault.osi_layer})</h3>
                            <p>${fault.root_cause}</p>
                            <h4>Fix Steps:</h4>
                            <ul>
                                ${fault.fix_steps.map(step => `<li>${step}</li>`).join('')}
                            </ul>
                        </div>`;
                        memoryString += `\\nFound Solution: ${fault.root_cause}`;
                    });
                    
                    // Add Review Buttons
                    replyHtml += `
                        <div style="margin-top: 15px; display: flex; gap: 10px;">
                            <button onclick="submitReview('ACCEPTED')" style="background:var(--accent); color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Accept Fix</button>
                            <button onclick="submitReview('REJECTED')" style="background:#ff4d4f; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Reject Fix</button>
                        </div>
                    `;
                }"""

new_block = """                if (ai.status === 'needs_info') {
                    if (ai.hypothesis_confidence) {
                        replyHtml += `<div style="margin-top: 10px; font-size: 12px; color: #888;">Working Theory Confidence: <span style="color:var(--accent)">${ai.hypothesis_confidence.toUpperCase()}</span></div>`;
                    }
                    if (ai.actionable_requests) {
                        ai.actionable_requests.forEach(req => {
                            replyHtml += `
                            <div class="cmd-request">
                                <div class="device-badge">Device: ${req.device}</div>
                                <div><em>Reason: ${req.reason}</em></div>
                                <code>${req.command}</code>
                            </div>`;
                            memoryString += `\\nRequested ${req.command} on ${req.device}`;
                        });
                    }
                } else if (ai.status === 'solution' && ai.faults) {
                    ai.faults.forEach((fault, idx) => {
                        let stepsHtml = '';
                        if (Array.isArray(fault.fix_steps) && fault.fix_steps.length > 0 && typeof fault.fix_steps[0] === 'object') {
                            fault.fix_steps.forEach(step => {
                                stepsHtml += `<div style="margin-bottom: 10px;">
                                    <strong>${step.device}:</strong> ${step.explanation}
                                    <pre style="background: black; padding: 10px; border-radius: 4px; color: #569cd6; font-family: monospace; white-space: pre-wrap; margin-top: 5px;">${step.commands.join('\\n')}</pre>
                                </div>`;
                            });
                        } else {
                            stepsHtml = `<ul>${fault.fix_steps.map(step => `<li>${step}</li>`).join('')}</ul>`;
                        }
                        
                        replyHtml += `
                        <div class="fault-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin:0; color:var(--accent)">Root Cause (Layer ${fault.osi_layer})</h3>
                                <span style="background: #2f2f2f; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Confidence: ${fault.confidence || 'N/A'}</span>
                            </div>
                            <p>${fault.root_cause}</p>
                            <h4>Fix Steps:</h4>
                            ${stepsHtml}
                        </div>`;
                        memoryString += `\\nFound Solution: ${fault.root_cause}`;
                    });
                    
                    if (ai.confidence_matrix) {
                        replyHtml += `
                        <div style="margin-top:15px; font-size: 12px; color: #aaa; background: #2f2f2f; padding: 10px; border-radius: 6px;">
                            <strong>Multi-Layer Confidence Matrix:</strong><br>
                            Layer 2: ${ai.confidence_matrix.layer_2 || 'N/A'} | Layer 3: ${ai.confidence_matrix.layer_3 || 'N/A'} | Layer 4-7: ${ai.confidence_matrix.layer_4_to_7 || 'N/A'}
                        </div>`;
                    }
                    
                    // Add Review Buttons
                    replyHtml += `
                        <div style="margin-top: 15px; display: flex; gap: 10px;">
                            <button onclick="submitReview('ACCEPTED')" style="background:var(--accent); color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Accept Fix</button>
                            <button onclick="submitReview('REJECTED')" style="background:#ff4d4f; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Reject Fix</button>
                        </div>
                    `;
                }"""

text = text.replace(old_block, new_block)
p.write_text(text, encoding='utf-8')
print("Successfully replaced JS block!")
