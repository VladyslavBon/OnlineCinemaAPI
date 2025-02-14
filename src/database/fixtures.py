import random

from sqlalchemy.orm import Session

from database.models.accounts import UserGroupModel, UserGroupEnum
from database.models.movies import MovieModel, GenreModel, DirectorModel, CertificationModel, StarModel


def load_fixtures(db: Session):
    user_groups = [
        UserGroupModel(name=UserGroupEnum.USER),
        UserGroupModel(name=UserGroupEnum.MODERATOR),
        UserGroupModel(name=UserGroupEnum.ADMIN),
    ]
    db.add_all(user_groups)
    db.commit()

    certifications = [
        CertificationModel(name="G"),
        CertificationModel(name="PG"),
        CertificationModel(name="PG-13"),
        CertificationModel(name="R"),
    ]
    db.add_all(certifications)
    db.commit()

    genres = [
        GenreModel(name="Action"),
        GenreModel(name="Drama"),
        GenreModel(name="Comedy"),
        GenreModel(name="Thriller"),
        GenreModel(name="Horror"),
        GenreModel(name="Sci-Fi"),
    ]
    db.add_all(genres)
    db.commit()

    directors = [
        DirectorModel(name="Christopher Nolan"),
        DirectorModel(name="Steven Spielberg"),
        DirectorModel(name="Quentin Tarantino"),
        DirectorModel(name="Martin Scorsese"),
    ]
    db.add_all(directors)
    db.commit()

    stars = [
        StarModel(name="Leonardo DiCaprio"),
        StarModel(name="Brad Pitt"),
        StarModel(name="Robert Downey Jr."),
        StarModel(name="Scarlett Johansson"),
        StarModel(name="Tom Hanks"),
    ]
    db.add_all(stars)
    db.commit()

    movies = [
        MovieModel(
            name=f"Movie {i}",
            year=2000 + i,
            time=random.randint(90, 180),
            imdb=round(random.uniform(6.0, 9.5), 1),
            votes=random.randint(10, 100),
            rating=round(random.uniform(6.0, 9.5), 1),
            meta_score=random.randint(50, 100),
            gross=round(random.uniform(10.0, 500.0), 2),
            description="Description for Movie",
            price=round(random.uniform(5.0, 20.0), 2),
            certification=random.choice(certifications),
            genres=random.sample(genres, k=random.randint(1, 3)),
            directors=random.sample(directors, k=random.randint(1, 2)),
            stars=random.sample(stars, k=random.randint(2, 4)),
        )
        for i in range(1, 21)
    ]

    db.add_all(movies)
    db.commit()
