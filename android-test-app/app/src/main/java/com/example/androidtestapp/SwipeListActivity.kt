package com.example.androidtestapp

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.ItemTouchHelper
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class SwipeListActivity : AppCompatActivity() {
    private lateinit var adapter: SwipeListAdapter
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_swipe_list)

        status = findViewById(R.id.swipe_status)
        val recyclerView = findViewById<RecyclerView>(R.id.swipe_list)
        recyclerView.layoutManager = LinearLayoutManager(this)

        adapter = SwipeListAdapter(mutableListOf())
        recyclerView.adapter = adapter

        findViewById<Button>(R.id.btn_reset_list).setOnClickListener {
            resetItems()
        }

        val touchHelper = ItemTouchHelper(
            object : ItemTouchHelper.SimpleCallback(0, ItemTouchHelper.LEFT or ItemTouchHelper.RIGHT) {
                override fun onMove(
                    recyclerView: RecyclerView,
                    viewHolder: RecyclerView.ViewHolder,
                    target: RecyclerView.ViewHolder,
                ): Boolean {
                    return false
                }

                override fun onSwiped(viewHolder: RecyclerView.ViewHolder, direction: Int) {
                    val position = viewHolder.bindingAdapterPosition
                    if (position == RecyclerView.NO_POSITION) {
                        return
                    }
                    val removed = adapter.removeAt(position)
                    status.text = "Removed: $removed"
                }
            }
        )
        touchHelper.attachToRecyclerView(recyclerView)

        resetItems()
    }

    private fun resetItems() {
        val items = (1..20).map { "Swipe Item $it" }
        adapter.replace(items)
        status.text = "Status: Ready"
    }
}
