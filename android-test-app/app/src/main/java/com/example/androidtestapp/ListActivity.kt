package com.example.androidtestapp

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView

class ListActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_list)

        val selectedText = findViewById<TextView>(R.id.selected_text)
        val recyclerView = findViewById<RecyclerView>(R.id.recycler_list)

        val items = (1..100).map { index -> "Item $index" }
        recyclerView.layoutManager = LinearLayoutManager(this)
        recyclerView.adapter = ItemAdapter(items) { item ->
            selectedText.text = "Selected: $item"
        }
    }
}

private class ItemAdapter(
    private val items: List<String>,
    private val onClick: (String) -> Unit,
) : RecyclerView.Adapter<ItemViewHolder>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ItemViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_list, parent, false)
        return ItemViewHolder(view, onClick)
    }

    override fun onBindViewHolder(holder: ItemViewHolder, position: Int) {
        holder.bind(items[position])
    }

    override fun getItemCount(): Int = items.size
}

private class ItemViewHolder(
    itemView: View,
    private val onClick: (String) -> Unit,
) : RecyclerView.ViewHolder(itemView) {

    private val titleView: TextView = itemView.findViewById(R.id.item_title)
    private var current: String? = null

    init {
        itemView.setOnClickListener {
            current?.let(onClick)
        }
    }

    fun bind(title: String) {
        current = title
        titleView.text = title
    }
}
