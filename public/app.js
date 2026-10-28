import {createClient} from '/_coders/sdk.js';
const client = createClient();
const title = document.getElementById('title');
const connection = document.getElementById('connection');
const form = document.querySelector('form');
const seen = new Set();
async function refresh() {
  const result = await client.request('/api/state');
  if (!result.ok) throw new Error(`문서를 읽지 못했습니다 (${result.status})`);
  title.textContent = result.data.document.title;
  if (document.activeElement !== form.elements.title) form.elements.title.value = result.data.document.title;
}
const stop = client.watchActivity({
  // 최초 접속과 이력 유실 시에는 현재 DB 데이터를 다시 읽습니다.
  async onReset() {await refresh(); connection.textContent='실시간으로 연결되었습니다.';},
  async onEvent(event) {
    if (event.changed) await refresh();
    if (!seen.has(event.cursor)) {
      const item = document.createElement('li');
      const who = event.actor_label || event.actor.kind;
      const action = event.action === 'save' ? '문서를 저장했습니다' : event.action;
      const time = new Date(event.created_at * 1000).toLocaleTimeString('ko-KR', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
      item.textContent = `${who} · ${action} · ${time}`;
      document.getElementById('empty-activity').hidden = true;
      document.getElementById('activity').prepend(item);
      seen.add(event.cursor);
      // 화면 이력도 제한해 장시간 사용 시 메모리가 계속 늘어나지 않게 합니다.
      if (seen.size > 100) { seen.delete(seen.values().next().value); document.querySelector('#activity li:last-child')?.remove(); }
    }
    connection.textContent = '실시간으로 연결되었습니다.';
  },
  onError(error) {connection.textContent = error.message;},
  highlight: true,
});
let pending = null;
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button');
  if (!pending) pending = {action_id:crypto.randomUUID(), title:form.elements.title.value, actor_label:'브라우저', key:crypto.randomUUID()};
  button.disabled = true;
  try {
    const result = await client.request('/api/save',{method:'PUT',headers:{'Content-Type':'application/json','Idempotency-Key':pending.key},body:JSON.stringify({action_id:pending.action_id,title:pending.title,actor_label:pending.actor_label})});
    if (!result.ok) throw new Error(`저장을 확인하지 못했습니다 (${result.status})`);
    await refresh();
    connection.textContent = result.data.activity_pending ? '저장되었습니다. 알림은 같은 요청으로 다시 전송할 수 있습니다.' : '저장되었습니다.';
    if (!result.data.activity_pending) pending = null;
    else pending.key = crypto.randomUUID(); // 저장 완료가 확인된 뒤 알림 발행만 새 요청으로 재시도합니다.
  } catch(error) {connection.textContent=error.message;}
  finally {button.disabled=false; form.elements.title.disabled=!!pending; button.textContent=pending ? '같은 저장 다시 확인' : '저장';}
});
window.addEventListener('pagehide',stop,{once:true});
