from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from configuraciones.utils import get_perfil_usuario
from core.notifications import grupo_notificaciones_tienda


class NotificacionesConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return

        tienda_id = await self._get_tienda_id(user)
        if not tienda_id:
            await self.close()
            return

        self.group_name = grupo_notificaciones_tienda(tienda_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        group_name = getattr(self, 'group_name', None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def notificacion_enviar(self, event):
        await self.send_json(event['payload'])

    @database_sync_to_async
    def _get_tienda_id(self, user):
        return get_perfil_usuario(user).tienda_id
