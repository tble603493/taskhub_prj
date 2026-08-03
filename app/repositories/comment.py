from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Comment)

    async def list_by_task(
        self,
        task_id: int,
    ) -> list[Comment]:
        result = await self.session.execute(
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_task(
        self,
        comment_id: int,
        task_id: int,
    ) -> Comment | None:
        result = await self.session.execute(
            select(Comment).where(
                Comment.id == comment_id,
                Comment.task_id == task_id,
            )
        )
        return result.scalar_one_or_none()
