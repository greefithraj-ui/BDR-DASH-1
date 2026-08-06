class BaseService:
    def __init__(self, repository):
        self.repository = repository
        
    def get_all(self):
        return self.repository.get_all()
