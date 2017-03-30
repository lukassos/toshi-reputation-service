import os
from tornado.testing import gen_test

from tokenrep.app import urls
from tokenservices.test.database import requires_database
from tokenservices.test.base import AsyncHandlerTest
from tokenservices.ethereum.utils import data_decoder, private_key_to_address

TEST_PRIVATE_KEY = data_decoder("0xe8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35")
TEST_ADDRESS = "0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"

TEST_ADDRESS_2 = "0x056db290f8ba3250ca64a45d16284d04bc000000"

class RatingsTest(AsyncHandlerTest):

    def get_urls(self):
        return urls

    def get_url(self, path):
        path = "/v1{}".format(path)
        return super().get_url(path)

    @gen_test
    @requires_database
    async def test_review_user(self):

        rating = 3.5
        message = "et fantastisk menneske"

        body = {
            "reviewee": TEST_ADDRESS_2,
            "rating": rating,
            "review": message
        }

        resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="POST", body=body)
        self.assertResponseCodeEqual(resp, 204)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['reviewer_address'], TEST_ADDRESS)
        self.assertEqual(rows[0]['rating'], rating)
        self.assertEqual(rows[0]['review'], message)

    @gen_test
    @requires_database
    async def test_fail_when_review_exists(self):

        message = "et fantastisk menneske"
        rating = 3.0
        reviews = [
            (TEST_ADDRESS, TEST_ADDRESS_2, rating, message)
        ]

        async with self.pool.acquire() as con:
            for rev in reviews:
                await con.execute(
                    "INSERT INTO reviews (reviewer_address, reviewee_address, rating, review) "
                    "VALUES ($1, $2, $3, $4)",
                    *rev)

        updated_message = "et veldig fantastisk menneske"
        updated_rating = 4.5

        body = {
            "reviewee": TEST_ADDRESS_2,
            "rating": updated_rating,
            "review": updated_message
        }

        resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="POST", body=body)
        self.assertResponseCodeEqual(resp, 400)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['reviewer_address'], TEST_ADDRESS)
        self.assertEqual(rows[0]['rating'], rating)
        self.assertEqual(rows[0]['review'], message)

    @gen_test
    @requires_database
    async def test_review_user_without_signing(self):

        rating = 3.5
        message = "et fantastisk menneske"

        body = {
            "reviewee": TEST_ADDRESS_2,
            "rating": rating,
            "review": message
        }

        resp = await self.fetch("/review/submit", method="POST", body=body)
        self.assertResponseCodeEqual(resp, 400)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

        self.assertEqual(len(rows), 0)

    @gen_test
    @requires_database
    async def test_review_with_invalid_rating(self):

        ratings = [5.5, "blah", None, -0.5, {"obj": 4}, "2/5",
                  # valid decimal.Decimal values that we don't want to accept
                  [0, [3, 1, 4], -2], 'NaN', 'Inf', '-NaN', '-INF', "infinity", "-infinity"]
        message = "et fantastisk menneske"

        for rating in ratings:
            body = {
                "reviewee": TEST_ADDRESS_2,
                "rating": rating,
                "review": message
            }

            resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="POST", body=body)
            self.assertResponseCodeEqual(resp, 400, "Expected rating '{}' to be invalid".format(rating))

            async with self.pool.acquire() as con:
                rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

            self.assertEqual(len(rows), 0)

    @gen_test
    @requires_database
    async def test_review_with_invalid_message(self):

        rating = 3.0
        messages = [
            10000,
            {"obj": 123},
            [0, [3, 1, 4], -2]
        ]

        for message in messages:
            body = {
                "reviewee": TEST_ADDRESS_2,
                "rating": rating,
                "review": message
            }

            resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="POST", body=body)
            self.assertResponseCodeEqual(resp, 400, "Expected message '{}' to be invalid".format(message))

            async with self.pool.acquire() as con:
                rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

            self.assertEqual(len(rows), 0)

    @gen_test
    @requires_database
    async def test_update_review(self):

        message = "et fantastisk menneske"
        rating = 3.0
        reviews = [
            (TEST_ADDRESS, TEST_ADDRESS_2, rating, message),
            (private_key_to_address(os.urandom(32)), TEST_ADDRESS_2, rating, message)
        ]

        async with self.pool.acquire() as con:
            for rev in reviews:
                await con.execute(
                    "INSERT INTO reviews (reviewer_address, reviewee_address, rating, review) "
                    "VALUES ($1, $2, $3, $4)",
                    *rev)

        updated_message = "et veldig fantastisk menneske"
        updated_rating = 4.5

        body = {
            "reviewee": TEST_ADDRESS_2,
            "rating": updated_rating,
            "review": updated_message
        }

        resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="PUT", body=body)
        self.assertResponseCodeEqual(resp, 204)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1 AND reviewer_address = $2", TEST_ADDRESS_2, TEST_ADDRESS)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['rating'], updated_rating)
        self.assertEqual(rows[0]['review'], updated_message)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1 AND reviewer_address != $2", TEST_ADDRESS_2, TEST_ADDRESS)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['rating'], rating)
        self.assertEqual(rows[0]['review'], message)

    @gen_test
    @requires_database
    async def test_fail_update_review_when_doesnt_exist(self):

        updated_message = "et veldig fantastisk menneske"
        updated_rating = 4.5

        body = {
            "reviewee": TEST_ADDRESS_2,
            "rating": updated_rating,
            "review": updated_message
        }

        resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="PUT", body=body)
        self.assertResponseCodeEqual(resp, 400)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1 AND reviewer_address = $2", TEST_ADDRESS_2, TEST_ADDRESS)

        self.assertEqual(len(rows), 0)

    @gen_test
    @requires_database
    async def test_delete_review(self):

        message = "et fantastisk menneske"
        rating = 3.0
        reviews = [
            (TEST_ADDRESS, TEST_ADDRESS_2, rating, message),
            (private_key_to_address(os.urandom(32)), TEST_ADDRESS_2, rating, message)
        ]

        async with self.pool.acquire() as con:
            for rev in reviews:
                await con.execute(
                    "INSERT INTO reviews (reviewer_address, reviewee_address, rating, review) "
                    "VALUES ($1, $2, $3, $4)",
                    *rev)

        resp = await self.fetch_signed("/review/delete", signing_key=TEST_PRIVATE_KEY, method="POST",
                                       body={"reviewee": TEST_ADDRESS_2})
        self.assertResponseCodeEqual(resp, 204)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['reviewer_address'], reviews[1][0])

    @gen_test
    @requires_database
    async def test_user_cannot_review_themselves(self):

        rating = 5.0
        message = "et fantastisk menneske"

        body = {
            "reviewee": TEST_ADDRESS,
            "rating": rating,
            "review": message
        }

        resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="POST", body=body)
        self.assertResponseCodeEqual(resp, 400)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS)

        self.assertEqual(len(rows), 0)

    @gen_test
    @requires_database
    async def test_user_address_case_ignored(self):

        rating = 5.0
        message = "et fantastisk menneske"

        body = {
            "reviewee": "0x{}".format(TEST_ADDRESS_2[2:].upper()),
            "rating": rating,
            "review": message
        }

        resp = await self.fetch_signed("/review/submit", signing_key=TEST_PRIVATE_KEY, method="POST", body=body)
        self.assertResponseCodeEqual(resp, 204)

        async with self.pool.acquire() as con:
            rows = await con.fetch("SELECT * FROM reviews WHERE reviewee_address = $1", TEST_ADDRESS_2)

        self.assertEqual(len(rows), 1)
