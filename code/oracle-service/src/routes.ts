import express from 'express';
import cors from 'cors';
const router = express.Router();
router.use(cors());

import {
    getOracleData,
    updateOracleData,
    deleteOracleEntry  // <-- new function to handle deletion
} from "./controller";

// -------------------- Execute --------------------
// Update oracle data
router.route('/oracle-data').post(updateOracleData);

// Delete a specific wallet entry
router.route('/delete-oracle-entry').post(deleteOracleEntry);

// -------------------- Queries --------------------
// Get oracle data
router.route('/oracle-data').get(getOracleData);

export default router;
