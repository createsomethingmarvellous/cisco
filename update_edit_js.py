import pathlib
import re

p = pathlib.Path('templates/index.html')
text = p.read_text(encoding='utf-8')

old_buttons = """                    // Add Review Buttons
                    replyHtml += `
                        <div style="margin-top: 15px; display: flex; gap: 10px;">
                            <button onclick="submitReview('ACCEPTED')" style="background:var(--accent); color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Accept Fix</button>
                            <button onclick="submitReview('REJECTED')" style="background:#ff4d4f; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Reject Fix</button>
                        </div>
                    `;"""

new_buttons = """                    // Add Review Buttons
                    let reviewId = 'review-' + Math.random().toString(36).substr(2, 9);
                    replyHtml += `
                        <div style="margin-top: 15px; display: flex; gap: 10px;">
                            <button onclick="submitReview('ACCEPTED', '${reviewId}')" style="background:var(--accent); color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Accept Fix</button>
                            <button onclick="submitReview('REJECTED', '${reviewId}')" style="background:#ff4d4f; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Reject Fix</button>
                            <button onclick="toggleEdit('${reviewId}')" style="background:#555; color:white; border:none; padding:8px 15px; border-radius:4px; cursor:pointer;">Edit Fix</button>
                        </div>
                        <div id="edit-box-${reviewId}" style="display:none; margin-top: 10px;">
                            <textarea id="edit-text-${reviewId}" placeholder="Enter correct human fix..." style="width: 100%; box-sizing: border-box; background: #2f2f2f; color: white; border: 1px solid #555; border-radius: 4px; padding: 8px; margin-bottom: 5px;"></textarea>
                            <button onclick="submitReview('EDITED', '${reviewId}')" style="background:#ff9800; color:white; border:none; padding:6px 12px; border-radius:4px; cursor:pointer;">Submit Edit</button>
                        </div>
                    `;"""

old_submit = """        async function submitReview(decision) {
            const lastAiMessage = chatHistory[chatHistory.length - 1];
            await fetch('/api/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ decision: decision, ai_diagnosis: { root_cause: lastAiMessage.content } })
            });
            fetchStats();
            alert(`Review submitted: ${decision}. Thanks for helping improve the model!`);
        }"""

new_submit = """        async function submitReview(decision, reviewId) {
            let feedback = '';
            if (decision === 'EDITED') {
                const textEl = document.getElementById('edit-text-' + reviewId);
                if (textEl) {
                    feedback = textEl.value.trim();
                    if (!feedback) {
                        alert("Please enter the correct fix before submitting.");
                        return;
                    }
                }
            }
            
            const lastAiMessage = chatHistory[chatHistory.length - 1];
            await fetch('/api/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ decision: decision, feedback: feedback, ai_diagnosis: { root_cause: lastAiMessage.content } })
            });
            fetchStats();
            alert(`Review submitted: ${decision}. Thanks for helping improve the model!`);
        }

        function toggleEdit(reviewId) {
            const box = document.getElementById('edit-box-' + reviewId);
            if (box) {
                box.style.display = box.style.display === 'none' ? 'block' : 'none';
            }
        }"""

text = text.replace(old_buttons, new_buttons)
text = text.replace(old_submit, new_submit)
p.write_text(text, encoding='utf-8')
print("Successfully replaced JS blocks!")
